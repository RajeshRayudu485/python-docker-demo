import os
import socket
import time
import json
import platform
from datetime import datetime

import psutil
from flask import Flask, jsonify, render_template, Response, stream_with_context

app = Flask(__name__)


def snapshot():
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    return {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "cpu": round(psutil.cpu_percent(interval=None), 1),
        "cpu_cores": psutil.cpu_count(),
        "memory": round(vm.percent, 1),
        "memory_used_gb": round(vm.used / (1024 ** 3), 2),
        "memory_total_gb": round(vm.total / (1024 ** 3), 2),
        "disk": round(du.percent, 1),
        "disk_used_gb": round(du.used / (1024 ** 3), 2),
        "disk_total_gb": round(du.total / (1024 ** 3), 2),
        "processes": len(psutil.pids()),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M"),
        "uptime": str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split(".")[0],
    }


@app.get("/")
def home():
    return render_template(
        "index.html",
        hostname=socket.gethostname(),
        platform=platform.system(),
    )


@app.get("/health")
def health():
    return jsonify(status="healthy", hostname=socket.gethostname()), 200


@app.get("/api/snapshot")
def api_snapshot():
    return jsonify(snapshot()), 200


@app.get("/stream")
def stream():
    @stream_with_context
    def gen():
        # Prime CPU sampler (first call is always 0.0)
        psutil.cpu_percent(interval=None)
        while True:
            yield f"data: {json.dumps(snapshot())}\n\n"
            time.sleep(1)
    return Response(
        gen(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.errorhandler(404)
def not_found(_e):
    return jsonify(error="page not found"), 404


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)
