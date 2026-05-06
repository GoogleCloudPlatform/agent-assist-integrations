# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential

# 1. Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Copy the self-contained context (locustfile, local proto/, local audio/)
COPY . .

# 3. Compile protos (they are in the local proto/ folder now)
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=. \
    --grpc_python_out=. \
    ./proto/voice.proto

# Launcher script 
# 1. We use $PORT variable provided by Cloud Run
# 2. We bind to 0.0.0.0
# 3. We use 'exec' for the master to ensure it receives health check signals
RUN echo '#!/bin/bash\n\
# Start workers in the background\n\
for i in {1..3}; do \n\
  locust -f locustfile.py --worker --master-port 5557 & \n\
done\n\
\n\
# Start master in the foreground and bind to the assigned port\n\
exec locust -f locustfile.py --master --master-bind-port 5557 --web-host 0.0.0.0 --web-port ${PORT:-8089}' > /app/start.sh && chmod +x /app/start.sh

ENTRYPOINT ["/app/start.sh"]