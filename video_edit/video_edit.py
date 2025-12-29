"""Local-first video editing assistant using FFmpeg, Whisper, and Ollama.

Workflows:
- Longform: ingest raw footage, transcribe, ask an LLM for an edit plan, cut/concat.
- Shorts: generate vertical clips for Shorts/Reels/TikTok with burnt-in captions optional.

This script is intentionally dependency-light: it shells out to FFmpeg, Whisper CLI,
and Ollama. You must have those tools installed and on PATH. GPU acceleration is
controlled by those tools' own flags (not handled here).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


# Defaults you can override via CLI or config
DEFAULT_WHISPER_MODEL = "medium"
DEFAULT_OLLAMA_MODEL = "llama3:8b"
DEFAULT_WORKDIR = "./.video_work"
DEFAULT_MAX_CLIPS = 6
DEFAULT_SHORT_MAX_DURATION = 60.0


class CommandError(RuntimeError):
	pass


def load_config(config_path: Optional[str]) -> dict:
	"""Load JSON config if provided or if default file exists."""
	if config_path:
		path = Path(config_path).expanduser().resolve()
		if not path.exists():
			raise CommandError(f"Config file not found: {path}")
	else:
		path = Path("video_edit.config.json")
		if not path.exists():
			return {}
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except Exception as exc:  # noqa: BLE001
		raise CommandError(f"Failed to parse config file {path}: {exc}") from exc


def pick(value, cfg_value, default):
	"""Return CLI value if set, else config value, else default."""
	if value is not None:
		return value
	if cfg_value is not None:
		return cfg_value
	return default


def run_cmd(cmd: List[str], cwd: Optional[Path] = None) -> str:
	"""Run a shell command and return stdout; raises on non-zero exit."""
	result = subprocess.run(
		cmd,
		cwd=str(cwd) if cwd else None,
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		check=False,
	)
	if result.returncode != 0:
		raise CommandError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
	return result.stdout.strip()


def ensure_tool(name: str, probe_args: List[str]) -> None:
	"""Check that a CLI tool is available."""
	try:
		run_cmd([name, *probe_args])
	except Exception as exc:  # noqa: BLE001
		raise CommandError(f"Missing required tool '{name}': {exc}") from exc


def get_video_duration(input_video: Path) -> float:
	"""Return video duration in seconds using ffprobe."""
	stdout = run_cmd(
		[
			"ffprobe",
			"-v",
			"error",
			"-show_entries",
			"format=duration",
			"-of",
			"default=noprint_wrappers=1:nokey=1",
			str(input_video),
		]
	)
	try:
		return float(stdout)
	except ValueError as exc:  # noqa: BLE001
		raise CommandError(f"Could not parse duration from ffprobe output: {stdout}") from exc


def extract_audio(input_video: Path, output_wav: Path) -> None:
	cmd = [
		"ffmpeg",
		"-y",
		"-i",
		str(input_video),
		"-ac",
		"1",
		"-ar",
		"16000",
		str(output_wav),
	]
	run_cmd(cmd)


def transcribe_with_whisper(audio_path: Path, output_json: Path, model: str) -> dict:
	"""Call Whisper CLI to transcribe audio to JSON; returns parsed JSON."""
	cmd = [
		"whisper",
		str(audio_path),
		"--model",
		model,
		"--output_format",
		"json",
		"--output_dir",
		str(output_json.parent),
	]
	run_cmd(cmd)
	transcript_path = audio_path.with_suffix(".json")
	if not transcript_path.exists():
		raise CommandError(f"Expected transcript at {transcript_path}, but it was not created.")
	output_json.write_bytes(transcript_path.read_bytes())
	return json.loads(output_json.read_text(encoding="utf-8"))


def transcript_text_from_json(transcript: dict) -> str:
	segments = transcript.get("segments", [])
	texts = [seg.get("text", "").strip() for seg in segments]
	return " ".join(t for t in texts if t)


def ollama_generate_plan(prompt: str, model: str) -> List[dict]:
	"""Call Ollama and expect JSON array output; falls back to empty list on parse failure."""
	cmd = ["ollama", "run", model]
	try:
		stdout = run_cmd(cmd, cwd=None)
		if not stdout.strip():
			return []
		return json.loads(stdout)
	except Exception as exc:  # noqa: BLE001
		raise CommandError(f"Ollama generation failed: {exc}") from exc


def build_plan_prompt(transcript_text: str, mode: str, max_clips: int, duration: float) -> str:
	return (
		"You are an expert video editor. Given the transcript, propose concise, high-energy clips "
		f"for {mode}. Output JSON array with objects: start_sec, end_sec, title, hook, description. "
		f"Total clips <= {max_clips}. Keep each clip under 90s for shorts and under {int(duration)}s for longform. "
		f"Transcript: {transcript_text[:8000]}"
	)


@dataclass
class ClipPlan:
	start_sec: float
	end_sec: float
	title: str
	hook: str
	description: str


def parse_plan(items: Iterable[dict], duration: float) -> List[ClipPlan]:
	plans: List[ClipPlan] = []
	for item in items:
		try:
			start = max(0.0, float(item.get("start_sec", 0)))
			end = float(item.get("end_sec", 0))
			if end <= start:
				continue
			if start >= duration:
				continue
			end = min(end, duration)
			plans.append(
				ClipPlan(
					start_sec=start,
					end_sec=end,
					title=str(item.get("title", "")),
					hook=str(item.get("hook", "")),
					description=str(item.get("description", "")),
				)
			)
		except Exception:  # noqa: BLE001
			continue
	return plans


def cut_segment(
	input_video: Path,
	start: float,
	end: float,
	output_path: Path,
	vf_filter: Optional[str] = None,
	burn_subtitle: Optional[Path] = None,
) -> None:
	duration = max(0, end - start)
	cmd = [
		"ffmpeg",
		"-y",
		"-ss",
		f"{start:.2f}",
		"-i",
		str(input_video),
		"-t",
		f"{duration:.2f}",
	]
	if burn_subtitle:
		vf_parts = [vf_filter] if vf_filter else []
		vf_parts.append(f"subtitles={burn_subtitle.as_posix()}")
		vf_filter = ",".join(vf_parts)
	if vf_filter:
		cmd += ["-vf", vf_filter]
	cmd += ["-c:v", "libx264", "-c:a", "aac", str(output_path)]
	run_cmd(cmd)


def concat_videos(inputs: List[Path], output_path: Path) -> None:
	with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
		for clip in inputs:
			f.write(f"file '{clip.as_posix()}'\n")
		list_path = Path(f.name)
	cmd = [
		"ffmpeg",
		"-y",
		"-f",
		"concat",
		"-safe",
		"0",
		"-i",
		str(list_path),
		"-c",
		"copy",
		str(output_path),
	]
	run_cmd(cmd)


def ensure_dependencies() -> None:
	ensure_tool("ffmpeg", ["-version"])
	ensure_tool("ffprobe", ["-version"])
	ensure_tool("whisper", ["--help"])
	ensure_tool("ollama", ["--help"])


def generate_plan(
	input_video: Path,
	work_dir: Path,
	whisper_model: str,
	ollama_model: str,
	mode: str,
	max_clips: int,
) -> List[ClipPlan]:
	work_dir.mkdir(parents=True, exist_ok=True)
	audio_path = work_dir / "audio.wav"
	transcript_path = work_dir / "transcript.json"
	print("[INFO] Extracting audio...")
	extract_audio(input_video, audio_path)
	print("[INFO] Transcribing...")
	transcript = transcribe_with_whisper(audio_path, transcript_path, whisper_model)
	transcript_text = transcript_text_from_json(transcript)
	duration = get_video_duration(input_video)
	prompt = build_plan_prompt(transcript_text, mode=mode, max_clips=max_clips, duration=duration)
	print("[INFO] Requesting edit plan from Ollama...")
	raw_plan = ollama_generate_plan(prompt, ollama_model)
	plans = parse_plan(raw_plan, duration)
	if not plans:
		print("[WARN] No clips returned by LLM; falling back to a single full-length segment.")
		plans = [ClipPlan(0.0, min(60.0, duration), title="Clip", hook="", description="")]
	return plans


def run_longform(args: argparse.Namespace, config: dict) -> None:
	ensure_dependencies()
	common_cfg = config.get("common", {})
	long_cfg = config.get("longform", {})
	input_video = Path(args.input).expanduser().resolve()
	output = Path(args.output).expanduser().resolve()
	work_dir = Path(pick(args.workdir, common_cfg.get("workdir"), DEFAULT_WORKDIR)).expanduser().resolve()
	whisper_model = pick(args.whisper_model, common_cfg.get("whisper_model"), DEFAULT_WHISPER_MODEL)
	ollama_model = pick(args.ollama_model, common_cfg.get("ollama_model"), DEFAULT_OLLAMA_MODEL)
	max_clips = int(pick(args.max_clips, long_cfg.get("max_clips"), DEFAULT_MAX_CLIPS))
	plans = generate_plan(
		input_video=input_video,
		work_dir=work_dir,
		whisper_model=whisper_model,
		ollama_model=tollama_model,
		mode="longform",
		max_clips=max_clips,
	)
	clips: List[Path] = []
	print("[INFO] Cutting clips...")
	for idx, plan in enumerate(plans):
		clip_path = work_dir / f"clip_{idx:02d}.mp4"
		cut_segment(input_video, plan.start_sec, plan.end_sec, clip_path)
		clips.append(clip_path)
	print("[INFO] Concatenating...")
	concat_videos(clips, output)
	print(f"[DONE] Longform edit saved to {output}")


def run_shorts(args: argparse.Namespace, config: dict) -> None:
	ensure_dependencies()
	common_cfg = config.get("common", {})
	short_cfg = config.get("shorts", {})
	input_video = Path(args.input).expanduser().resolve()
	output_dir = Path(args.output_dir).expanduser().resolve()
	work_dir = Path(pick(args.workdir, common_cfg.get("workdir"), DEFAULT_WORKDIR)).expanduser().resolve()
	whisper_model = pick(args.whisper_model, common_cfg.get("whisper_model"), DEFAULT_WHISPER_MODEL)
	ollama_model = pick(args.ollama_model, common_cfg.get("ollama_model"), DEFAULT_OLLAMA_MODEL)
	max_clips = int(pick(args.max_clips, short_cfg.get("max_clips"), DEFAULT_MAX_CLIPS))
	max_duration = float(pick(args.max_duration, short_cfg.get("max_duration"), DEFAULT_SHORT_MAX_DURATION))
	vertical = bool(pick(args.vertical, short_cfg.get("vertical"), False))
	duration = get_video_duration(input_video)
	plans = generate_plan(
		input_video=input_video,
		work_dir=work_dir,
		whisper_model=whisper_model,
		ollama_model=tollama_model,
		mode="shorts",
		max_clips=max_clips,
	)
	output_dir.mkdir(parents=True, exist_ok=True)
	vf_filter = "scale=-2:1080,crop=1080:1920" if vertical else None
	print("[INFO] Rendering short clips...")
	for idx, plan in enumerate(plans[: max_clips]):
		start = plan.start_sec
		end = min(plan.end_sec, start + max_duration)
		clip_path = output_dir / f"short_{idx:02d}.mp4"
		cut_segment(input_video, start, end, clip_path, vf_filter=vf_filter)
		meta = {
			"title": plan.title or f"Clip {idx+1}",
			"hook": plan.hook,
			"description": plan.description,
			"start_sec": start,
			"end_sec": end,
		}
		(clip_path.with_suffix(".json")).write_text(json.dumps(meta, indent=2), encoding="utf-8")
	print(f"[DONE] Shorts saved under {output_dir}")


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Local AI video editing pipeline")
	parser.add_argument("--config", default=None, help="path to JSON config (default: video_edit.config.json if present)")
	sub = parser.add_subparsers(dest="command", required=True)

	common = argparse.ArgumentParser(add_help=False)
	common.add_argument("--whisper-model", default=None)
	common.add_argument("--ollama-model", default=None)
	common.add_argument("--workdir", default=None, help="scratch directory")
	common.add_argument("--max-clips", type=int, default=None)

	longform = sub.add_parser("longform", parents=[common], help="Create a longform edit")
	longform.add_argument("--input", required=True)
	longform.add_argument("--output", required=True)
	longform.set_defaults(func=run_longform)

	shorts = sub.add_parser("shorts", parents=[common], help="Create short-form clips")
	shorts.add_argument("--input", required=True)
	shorts.add_argument("--output-dir", required=True)
	shorts.add_argument("--max-duration", type=float, default=None, help="max seconds per clip")
	shorts.add_argument(
		"--vertical",
		action=argparse.BooleanOptionalAction,
		default=None,
		help="force 9:16 framing (or use --no-vertical to disable if config enables)",
	)
	shorts.set_defaults(func=run_shorts)

	return parser


def main(argv: Optional[List[str]] = None) -> None:
	parser = build_parser()
	args = parser.parse_args(argv)
	try:
		config = load_config(args.config)
		args.func(args, config)
	except CommandError as exc:
		print(f"[ERROR] {exc}", file=sys.stderr)
		sys.exit(1)


if __name__ == "__main__":
	main()
