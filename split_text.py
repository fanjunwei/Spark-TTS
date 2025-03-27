import argparse
from pathlib import Path


def main(file_path: str):
    lines = []
    name = None
    index = 0
    output_dir = Path(file_path).parent / "output"
    print(output_dir)
    output_dir.mkdir(exist_ok=True)
    with open(file_path, "r") as f:
        for line in f:
            text = line.strip()
            if text and text[0] == "*" and text[-1] == "*":
                if name is not None:
                    with open(output_dir / f"{index:03d}_{name}.txt", "w") as f:
                        f.write("\n".join(lines))
                    lines = []
                    index += 1
                name = text[1:-1]
            else:
                lines.append(text)

    if name is not None:
        with open(output_dir / f"{index:03d}_{name}.txt", "w") as f:
            f.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file_path", type=str, required=True)
    args = parser.parse_args()
    main(args.file_path)
