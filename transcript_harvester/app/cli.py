import argparse
import json
from pathlib import Path

from app.core.config import get_settings
from app.schemas import TranscriptDumpRequest
from app.services.harvest_service import HarvestService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcript Scraper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dump_parser = subparsers.add_parser("dump", help="Fetch transcripts for a channel")
    dump_parser.add_argument("--channel-id")
    dump_parser.add_argument("--channel-url")
    dump_parser.add_argument("--channel-handle")
    dump_parser.add_argument("--search-query")
    dump_parser.add_argument("--max-videos", type=int, default=10)
    dump_parser.add_argument("--languages", nargs="+", default=["en"])
    dump_parser.add_argument("--refresh", action="store_true")
    dump_parser.add_argument("--output")
    dump_parser.add_argument("--persist-dump-file", action="store_true")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = get_settings()
    service = HarvestService(settings)

    if args.command == "dump":
        request = TranscriptDumpRequest(
            channel_id=args.channel_id,
            channel_url=args.channel_url,
            channel_handle=args.channel_handle,
            search_query=args.search_query,
            max_videos=args.max_videos,
            languages=args.languages,
            refresh=args.refresh,
            persist_dump_file=args.persist_dump_file,
        )
        response = service.fetch_transcript_dump(request)

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(response.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            print(output_path)
            return

        print(json.dumps(response.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
