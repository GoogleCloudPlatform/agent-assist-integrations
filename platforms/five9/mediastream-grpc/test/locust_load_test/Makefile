# --- Configuration ---
NUM_WORKERS=20
HOST=https://five9-mediastream-grpc-798656365078.us-central1.run.app
# Automatically use your system's hard limit (65535)
FD_LIMIT=$(shell ulimit -Hn)

.PHONY: run-locust stop-locust status

# 1. Clean up old runs
stop-locust:
	@echo "🛑 Killing existing Locust processes..."
	-@pkill -9 -f locust > /dev/null 2>&1 || true
	@sleep 1

# 2. Start the swarm
run-locust:
	@echo "🚀 Starting Master (FD Limit: $(FD_LIMIT))..."
	mkdir -p logs/
	@sh -c "ulimit -n $(FD_LIMIT) ; nohup locust -f locustfile.py --master --host $(HOST) > logs/master.log 2>&1 &"
	@sleep 3
	@echo "🛠️ Spawning $(NUM_WORKERS) workers..."
	@for i in $$(seq 1 $(NUM_WORKERS)); do \
		sh -c "ulimit -n $(FD_LIMIT) ; nohup locust -f locustfile.py --worker --master-host localhost > logs/worker_$$i.log 2>&1 &"; \
	done
	@echo "✅ Swarm launched! Access UI at http://localhost:8089"
	@echo "📊 Run 'make status' to verify workers."

# 3. Verify health
status:
	@echo "🖥️  Locust Processes:"
	@pgrep -fl locust || echo "No locust processes found."
	@echo "\n📈 Worker Connection Count (from Master log):"
	@grep -i "worker" logs/master.log | tail -n 5 || echo "No connections logged yet."

# Monitor the open file count of all locust processes combined
monitor-sockets:
	@echo "📊 Total open sockets/files for Locust:"
	@lsof -nP -p $$(pgrep -d, -f locust) 2>/dev/null | wc -l
