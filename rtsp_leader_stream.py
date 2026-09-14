#!/usr/bin/env python3
import argparse
import os
import random
import socket
import socketserver
import struct
import threading
import time

import cv2
import numpy as np


DEFAULT_IMAGE = "/home/jiacdi/bordershield_ai/latest_detection.jpg"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8554
DEFAULT_PATH = "/bordershield"
DEFAULT_FPS = 5
JPEG_QUALITY = 75
MAX_RTP_PAYLOAD = 1200


def timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def extract_jpeg_scan(jpeg_bytes):
    if len(jpeg_bytes) < 4 or jpeg_bytes[0:2] != b"\xff\xd8":
        raise ValueError("not a JPEG image")

    i = 2
    while i + 4 < len(jpeg_bytes):
        if jpeg_bytes[i] != 0xFF:
            i += 1
            continue

        while i < len(jpeg_bytes) and jpeg_bytes[i] == 0xFF:
            i += 1
        if i >= len(jpeg_bytes):
            break

        marker = jpeg_bytes[i]
        i += 1

        if marker == 0xDA:  # SOS
            length = (jpeg_bytes[i] << 8) | jpeg_bytes[i + 1]
            scan_start = i + length
            scan_end = jpeg_bytes.rfind(b"\xff\xd9")
            if scan_end < scan_start:
                scan_end = len(jpeg_bytes)
            return jpeg_bytes[scan_start:scan_end]

        if marker == 0xD9:
            break

        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue

        length = (jpeg_bytes[i] << 8) | jpeg_bytes[i + 1]
        i += length

    raise ValueError("JPEG SOS marker not found")


def read_encoded_frame(image_path):
    data = cv2.imread(image_path)
    if data is None:
        raise ValueError("could not read " + image_path)

    if data.shape[1] != 640 or data.shape[0] != 480:
        data = cv2.resize(data, (640, 480))

    ok, encoded = cv2.imencode(".jpg", data, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:
        raise ValueError("could not encode JPEG")

    jpeg_bytes = encoded.tobytes()
    scan = extract_jpeg_scan(jpeg_bytes)
    return scan, data.shape[1], data.shape[0]


def make_rtp_header(seq, rtp_timestamp, marker, payload_type, ssrc):
    b0 = 0x80
    b1 = payload_type & 0x7F
    if marker:
        b1 |= 0x80
    return struct.pack("!BBHII", b0, b1, seq & 0xFFFF, rtp_timestamp & 0xFFFFFFFF, ssrc)


def make_jpeg_header(fragment_offset, width, height):
    return struct.pack(
        "!B3sBBBB",
        0,
        int(fragment_offset).to_bytes(3, byteorder="big"),
        1,
        JPEG_QUALITY,
        max(1, min(255, width // 8)),
        max(1, min(255, height // 8)),
    )


class StreamState:
    def __init__(self, server, client_address, transport, client_ports=None, interleaved=(0, 1)):
        self.server = server
        self.client_address = client_address
        self.transport = transport
        self.client_ports = client_ports
        self.interleaved = interleaved
        self.session_id = str(random.randint(100000, 999999))
        self.stop_event = threading.Event()
        self.thread = None
        self.udp_socket = None
        self.seq = random.randint(0, 65535)
        self.rtp_timestamp = random.randint(0, 0xFFFFFFFF)
        self.ssrc = random.randint(1, 0xFFFFFFFF)

    def start(self, rtsp_socket=None):
        if self.thread and self.thread.is_alive():
            return

        if self.transport == "udp":
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(rtsp_socket,))
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.udp_socket:
            self.udp_socket.close()
            self.udp_socket = None

    def _send_packet(self, packet, rtsp_socket):
        if self.transport == "tcp":
            frame = b"$" + bytes([self.interleaved[0]]) + struct.pack("!H", len(packet)) + packet
            rtsp_socket.sendall(frame)
        else:
            self.udp_socket.sendto(packet, (self.client_address[0], self.client_ports[0]))

    def _run(self, rtsp_socket):
        frame_interval = 1.0 / float(self.server.fps)
        timestamp_step = int(90000 / float(self.server.fps))
        print("{} RTSP stream started for {} via {}".format(timestamp(), self.client_address[0], self.transport))

        while not self.stop_event.is_set():
            start = time.time()
            try:
                scan, width, height = read_encoded_frame(self.server.image_path)
                offset = 0
                while offset < len(scan) and not self.stop_event.is_set():
                    chunk_size = min(MAX_RTP_PAYLOAD, len(scan) - offset)
                    chunk = scan[offset:offset + chunk_size]
                    marker = (offset + chunk_size) >= len(scan)
                    jpeg_header = make_jpeg_header(offset, width, height)
                    rtp_header = make_rtp_header(self.seq, self.rtp_timestamp, marker, 26, self.ssrc)
                    self._send_packet(rtp_header + jpeg_header + chunk, rtsp_socket)
                    self.seq = (self.seq + 1) & 0xFFFF
                    offset += chunk_size
                self.rtp_timestamp = (self.rtp_timestamp + timestamp_step) & 0xFFFFFFFF
            except Exception as exc:
                print("{} RTSP stream warning: {}".format(timestamp(), exc))

            elapsed = time.time() - start
            sleep_for = max(0.01, frame_interval - elapsed)
            self.stop_event.wait(sleep_for)

        print("{} RTSP stream stopped for {}".format(timestamp(), self.client_address[0]))


class RTSPHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.stream = None
        self.buffer = b""

    def handle(self):
        while True:
            data = self.request.recv(4096)
            if not data:
                break
            self.buffer += data
            while b"\r\n\r\n" in self.buffer:
                raw, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
                keep_going = self.handle_request(raw.decode("utf-8", errors="replace"))
                if not keep_going:
                    return

    def finish(self):
        if self.stream:
            self.stream.stop()

    def handle_request(self, request_text):
        lines = request_text.split("\r\n")
        if not lines:
            return True

        parts = lines[0].split()
        if len(parts) < 3:
            return True

        method, url, _ = parts[:3]
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        cseq = headers.get("cseq", "1")
        method = method.upper()

        if method == "OPTIONS":
            self.send_response(cseq, 200, "OK", {"Public": "OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN"})
        elif method == "DESCRIBE":
            self.handle_describe(cseq)
        elif method == "SETUP":
            self.handle_setup(cseq, headers)
        elif method == "PLAY":
            self.handle_play(cseq)
        elif method == "TEARDOWN":
            self.send_response(cseq, 200, "OK", {"Session": self.session_id()})
            return False
        else:
            self.send_response(cseq, 405, "Method Not Allowed", {})
        return True

    def handle_describe(self, cseq):
        sdp = "\r\n".join([
            "v=0",
            "o=- 0 0 IN IP4 0.0.0.0",
            "s=BorderShield Leader AI",
            "c=IN IP4 0.0.0.0",
            "t=0 0",
            "a=control:*",
            "m=video 0 RTP/AVP 26",
            "a=control:streamid=0",
            "a=framerate:{}".format(self.server.fps),
            "",
        ])
        self.send_response(cseq, 200, "OK", {
            "Content-Type": "application/sdp",
            "Content-Base": "rtsp://{}:{}/{}".format(self.server.host_for_url, self.server.server_address[1], self.server.path.strip("/")),
        }, sdp)

    def handle_setup(self, cseq, headers):
        transport = headers.get("transport", "")
        if "RTP/AVP/TCP" in transport.upper():
            interleaved = (0, 1)
            if "interleaved=" in transport:
                try:
                    part = transport.split("interleaved=", 1)[1].split(";", 1)[0]
                    a, b = part.split("-", 1)
                    interleaved = (int(a), int(b))
                except Exception:
                    interleaved = (0, 1)
            self.stream = StreamState(self.server, self.client_address, "tcp", interleaved=interleaved)
            response_transport = "RTP/AVP/TCP;unicast;interleaved={}-{}".format(interleaved[0], interleaved[1])
        else:
            client_ports = (0, 0)
            if "client_port=" in transport:
                part = transport.split("client_port=", 1)[1].split(";", 1)[0]
                a, b = part.split("-", 1)
                client_ports = (int(a), int(b))
            self.stream = StreamState(self.server, self.client_address, "udp", client_ports=client_ports)
            response_transport = "RTP/AVP;unicast;client_port={}-{};server_port=50000-50001".format(client_ports[0], client_ports[1])

        self.send_response(cseq, 200, "OK", {
            "Transport": response_transport,
            "Session": self.stream.session_id,
        })

    def handle_play(self, cseq):
        if not self.stream:
            self.send_response(cseq, 454, "Session Not Found", {})
            return
        self.stream.start(self.request)
        self.send_response(cseq, 200, "OK", {
            "Session": self.stream.session_id,
            "RTP-Info": "url=rtsp://{}:{}/{};seq={};rtptime={}".format(
                self.server.host_for_url,
                self.server.server_address[1],
                self.server.path.strip("/"),
                self.stream.seq,
                self.stream.rtp_timestamp,
            ),
        })

    def session_id(self):
        return self.stream.session_id if self.stream else "000000"

    def send_response(self, cseq, code, reason, headers, body=None):
        response = [
            "RTSP/1.0 {} {}".format(code, reason),
            "CSeq: {}".format(cseq),
            "Server: BorderShield-RTSP",
        ]
        for key, value in headers.items():
            response.append("{}: {}".format(key, value))
        if body is not None:
            response.append("Content-Length: {}".format(len(body.encode("utf-8"))))
        response.append("")
        response.append(body or "")
        self.request.sendall("\r\n".join(response).encode("utf-8"))


class ThreadedRTSPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, handler_cls, image_path, fps, path, host_for_url):
        super(ThreadedRTSPServer, self).__init__(server_address, handler_cls)
        self.image_path = image_path
        self.fps = fps
        self.path = path
        self.host_for_url = host_for_url


def main():
    parser = argparse.ArgumentParser(description="BorderShield RTSP stream from latest_detection.jpg")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS)
    parser.add_argument("--host-for-url", default="169.254.59.226")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.image), exist_ok=True)
    server = ThreadedRTSPServer(
        (args.host, args.port),
        RTSPHandler,
        image_path=args.image,
        fps=args.fps,
        path=args.path,
        host_for_url=args.host_for_url,
    )

    print("{} BorderShield RTSP stream listening on rtsp://{}:{}{}".format(
        timestamp(),
        args.host_for_url,
        args.port,
        args.path,
    ))
    print("{} Streaming AI output image: {}".format(timestamp(), args.image))
    server.serve_forever()


if __name__ == "__main__":
    main()
