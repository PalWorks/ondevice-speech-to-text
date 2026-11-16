# SPDX-License-Identifier: AGPL-3.0-only
"""Speaker labels for dictate-live, run with the project venv (.venv/bin/python).

One process per session. Reads JSON lines on stdin, answers JSON lines on stdout:

  {"cmd": "assign", "id": 7, "path": "/run/.../p7.wav"}
      -> {"id": 7, "speaker": 1, "sim": 0.71}   (speaker null if the clip is too short)
  {"cmd": "final"}
      -> {"labels": {"7": 1, ...}, "speakers": 3}

"assign" gives a live label: the phrase's voice fingerprint (NeMo TitaNet small via
sherpa-onnx) is compared with the running average of each speaker so far. "final"
re-groups every fingerprint from scratch (average-linkage clustering), which is more
reliable than the live labels, and numbers speakers in order of first appearance.
"""
import json
import sys
import wave

import numpy as np
import sherpa_onnx

MIN_SECONDS = 1.0   # shorter clips give unreliable fingerprints
NEW_SPEAKER = 0.56  # below this similarity to every known speaker: a new speaker
FINAL_MERGE = 0.55  # final pass: merge groups whose average similarity is above this


def load(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def main():
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=sys.argv[1], num_threads=2))
    embs = {}       # phrase id -> unit vector
    centroids = []  # live speakers: [sum vector, count]
    for line in sys.stdin:
        msg = json.loads(line)
        if msg["cmd"] == "assign":
            audio = load(msg["path"])
            if len(audio) < MIN_SECONDS * 16000:
                reply = {"id": msg["id"], "speaker": None, "sim": None}
            else:
                stream = extractor.create_stream()
                stream.accept_waveform(16000, audio)
                stream.input_finished()
                e = np.array(extractor.compute(stream))
                e /= np.linalg.norm(e)
                embs[msg["id"]] = e
                sims = [float(e @ (c[0] / np.linalg.norm(c[0]))) for c in centroids]
                best = int(np.argmax(sims)) if sims else -1
                top = round(sims[best], 3) if sims else None
                if best < 0 or sims[best] < NEW_SPEAKER:
                    centroids.append([e.copy(), 1])
                    best = len(centroids) - 1
                else:
                    centroids[best][0] += e
                    centroids[best][1] += 1
                reply = {"id": msg["id"], "speaker": best, "sim": top}
        elif msg["cmd"] == "final":
            reply = final_labels(embs)
        else:
            reply = {"error": "unknown command"}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


def final_labels(embs):
    """Average-linkage clustering of every fingerprint (Lance-Williams updates on the
    similarity matrix, so an hour of phrases takes seconds)."""
    ids = sorted(embs)
    if not ids:
        return {"labels": {}, "speakers": 0}
    vec = np.array([embs[i] for i in ids])
    sim = vec @ vec.T
    np.fill_diagonal(sim, -np.inf)
    members = [[i] for i in ids]
    alive = np.ones(len(ids), dtype=bool)
    while alive.sum() > 1:
        masked = np.where(np.outer(alive, alive), sim, -np.inf)
        a, b = np.unravel_index(np.argmax(masked), masked.shape)
        if masked[a, b] < FINAL_MERGE:
            break
        na, nb = len(members[a]), len(members[b])
        row = (na * sim[a] + nb * sim[b]) / (na + nb)
        sim[a], sim[:, a] = row, row
        sim[a, a] = -np.inf
        members[a] += members[b]
        members[b] = []
        alive[b] = False
    groups = sorted((m for m in members if m), key=min)  # Speaker 1 is whoever spoke first
    labels = {str(i): n for n, g in enumerate(groups) for i in g}
    return {"labels": labels, "speakers": len(groups)}


if __name__ == "__main__":
    main()
