// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

using System.Buffers;

namespace DialogflowBidiStream.Buffers;

/// <summary>
/// High-performance, thread-safe circular ring buffer for caching raw audio frames.
/// Solves the CCaaS boundary lookback problem when rotating gRPC streams near 14.5 minutes.
/// </summary>
public sealed class CircularAudioBuffer : IDisposable
{
    private readonly byte[] _buffer;
    private readonly int _capacity;
    private readonly object _lock = new();

    private int _head; // Write cursor
    private int _count; // Current bytes stored
    private long _totalBytesWritten; // Monotonic counter for offset calculations
    private bool _disposed;

    /// <summary>
    /// Initializes a circular audio buffer sized for the given duration and audio specifications.
    /// </summary>
    /// <param name="maxDurationSeconds">Maximum history duration (e.g. 3.0 seconds).</param>
    /// <param name="sampleRateHertz">Audio sample rate (e.g. 8000 or 16000).</param>
    /// <param name="bytesPerSample">Bytes per sample (1 for MULAW, 2 for LINEAR16).</param>
    public CircularAudioBuffer(double maxDurationSeconds, int sampleRateHertz, int bytesPerSample = 1)
    {
        if (maxDurationSeconds <= 0) throw new ArgumentOutOfRangeException(nameof(maxDurationSeconds));
        if (sampleRateHertz <= 0) throw new ArgumentOutOfRangeException(nameof(sampleRateHertz));
        if (bytesPerSample <= 0) throw new ArgumentOutOfRangeException(nameof(bytesPerSample));

        int bytesPerSecond = sampleRateHertz * bytesPerSample;
        _capacity = (int)Math.Ceiling(maxDurationSeconds * bytesPerSecond);
        _buffer = ArrayPool<byte>.Shared.Rent(_capacity);
        _head = 0;
        _count = 0;
        _totalBytesWritten = 0;
    }

    /// <summary>
    /// Total bytes currently stored in the circular buffer.
    /// </summary>
    public int Count
    {
        get
        {
            lock (_lock) return _count;
        }
    }

    /// <summary>
    /// Total lifetime bytes written to this buffer across the stream.
    /// </summary>
    public long TotalBytesWritten
    {
        get
        {
            lock (_lock) return _totalBytesWritten;
        }
    }

    /// <summary>
    /// Appends incoming audio frames to the circular buffer.
    /// Overwrites older frames if the buffer reaches capacity.
    /// </summary>
    public void Write(ReadOnlySpan<byte> chunk)
    {
        if (chunk.IsEmpty) return;

        lock (_lock)
        {
            ObjectDisposedException.ThrowIf(_disposed, this);

            int chunkLen = chunk.Length;
            if (chunkLen >= _capacity)
            {
                // Chunk is larger than the entire buffer; retain only the most recent slice
                chunk[^_capacity..].CopyTo(_buffer.AsSpan(0, _capacity));
                _head = 0;
                _count = _capacity;
                _totalBytesWritten += chunkLen;
                return;
            }

            int firstCopy = Math.Min(chunkLen, _capacity - _head);
            chunk[..firstCopy].CopyTo(_buffer.AsSpan(_head, firstCopy));

            int secondCopy = chunkLen - firstCopy;
            if (secondCopy > 0)
            {
                chunk.Slice(firstCopy, secondCopy).CopyTo(_buffer.AsSpan(0, secondCopy));
            }

            _head = (_head + chunkLen) % _capacity;
            _count = Math.Min(_capacity, _count + chunkLen);
            _totalBytesWritten += chunkLen;
        }
    }

    /// <summary>
    /// Extracts the trailing unfinalized audio bytes recorded since the last recognized speech offset.
    /// If offset is zero or unfinalized audio exceeds maximum lookback, returns up to maxLookbackBytes.
    /// </summary>
    /// <param name="lastFinalOffset">Speech end offset of the last finalized transcript.</param>
    /// <param name="sampleRateHertz">Sample rate in Hertz.</param>
    /// <param name="bytesPerSample">Bytes per sample.</param>
    /// <param name="maxLookbackSeconds">Cap on lookback audio duration to avoid duplicate recognition.</param>
    /// <returns>Byte array of lookback audio to prepend to the new stream.</returns>
    public byte[] ExtractLookbackAudio(
        TimeSpan lastFinalOffset,
        int sampleRateHertz,
        int bytesPerSample = 1,
        double maxLookbackSeconds = 1.5)
    {
        lock (_lock)
        {
            ObjectDisposedException.ThrowIf(_disposed, this);

            if (_count == 0) return Array.Empty<byte>();

            int bytesPerSecond = sampleRateHertz * bytesPerSample;
            int maxLookbackBytes = (int)(maxLookbackSeconds * bytesPerSecond);

            // Calculate trailing bytes past last final speech boundary
            int trailingBytes;
            if (lastFinalOffset == TimeSpan.Zero)
            {
                trailingBytes = Math.Min(_count, maxLookbackBytes);
            }
            else
            {
                long finalOffsetBytes = (long)(lastFinalOffset.TotalSeconds * bytesPerSecond);
                long bytesSinceFinal = _totalBytesWritten - finalOffsetBytes;

                if (bytesSinceFinal <= 0)
                {
                    trailingBytes = 0;
                }
                else
                {
                    trailingBytes = (int)Math.Min(bytesSinceFinal, Math.Min(_count, maxLookbackBytes));
                }
            }

            if (trailingBytes <= 0)
            {
                return Array.Empty<byte>();
            }

            byte[] result = new byte[trailingBytes];
            int readStart = (_head - trailingBytes + _capacity) % _capacity;

            int firstRead = Math.Min(trailingBytes, _capacity - readStart);
            Array.Copy(_buffer, readStart, result, 0, firstRead);

            int secondRead = trailingBytes - firstRead;
            if (secondRead > 0)
            {
                Array.Copy(_buffer, 0, result, firstRead, secondRead);
            }

            return result;
        }
    }

    /// <summary>
    /// Clears the contents of the buffer.
    /// </summary>
    public void Clear()
    {
        lock (_lock)
        {
            _head = 0;
            _count = 0;
            _totalBytesWritten = 0;
        }
    }

    public void Dispose()
    {
        lock (_lock)
        {
            if (_disposed) return;
            _disposed = true;
            ArrayPool<byte>.Shared.Return(_buffer);
        }
    }
}
