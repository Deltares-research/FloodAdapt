import yaml
from pathlib import Path


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def save_yaml(data, path):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)


def extract_contents_only(sidebar_dict):
    sidebar = sidebar_dict.get("website", {}).get("sidebar", [])
    if isinstance(sidebar, list):
        sidebar = sidebar[0]
    return sidebar.get("contents", [])


def merge_flat_sections(api_sidebar_path, examples_sidebar_path, output_path):
    api_sidebar = load_yaml(api_sidebar_path)
    examples_sidebar = load_yaml(examples_sidebar_path)

    api_section = extract_contents_only(api_sidebar)
    examples_contents = extract_contents_only(examples_sidebar)

    merged_sidebar = {
        "website": {
            "sidebar": [
                {
                    "id": "dev_docs",
                    "title": "Developer Documentation",
                    "style": "docked",
                    "background": "light",
                    "search": True,
                    "collapse-level": 2,
                    "contents": [
                        {
                            "section": "Examples",
                            "href": "3_api_docs/examples/index.qmd",
                            "contents": examples_contents,
                        },
                        api_section,
                    ],
                }
            ]
        }
    }

    save_yaml(merged_sidebar, output_path)


if __name__ == "__main__":
    root = Path(__file__).parent.parent
    merge_flat_sections(
        api_sidebar_path=root / "3_api_docs/api_ref/_sidebar.yml",
        examples_sidebar_path=root / "3_api_docs/examples/_sidebar.yml",
        output_path=root / "3_api_docs/_sidebar.yml",
    )
