#!/usr/bin/env python

import argparse, os, subprocess, uuid, json, requests

OBSOLETE_FILES = [".travis.yml", "deploy_key.enc"]
TEMPLATES = {}
TEMPLATE_PARTS = {}
DB = json.loads(requests.get("https://github.com/whatwg/sg/raw/main/db.json").text)
FACTORY_DB = {}

def read_file(file):
    return open(file, "r", encoding="utf-8", newline="\n").read()

def write_file(file, contents):
    dirs = os.path.dirname(file)
    if dirs:
        os.makedirs(dirs, exist_ok=True)
    open(file, "w", encoding="utf-8", newline="\n").write(contents)

def href_to_shortname(href):
    return href[len("https://"):href.index(".")]

def find_files_with_extension(extension, recurse=True):
    paths = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(extension):
                path = os.path.relpath(os.path.join(root, file), start=".")
                paths.append(path)
        if not recurse:
            del dirs[:]
    return paths


def gather_files(extension):
    files = {}
    for path in find_files_with_extension(extension):
        files[path] = read_file(path)
    return files


def copy_and_fill_templates(variables):
    output = {}
    for template in TEMPLATES:
        output_name = template[:-len(".template")]
        output_contents = TEMPLATES[template]
        if output_name == "README.md":
            if variables["readme"]:
                output_contents += "\n" + TEMPLATE_PARTS[variables["readme"]]
            if os.path.isfile("READMEEND.md"):
                output_contents += "\n" + read_file("READMEEND.md")
        output[output_name] = fill_template(output_contents, variables)
    return output

def fill_template(contents, variables):
    for variable, data in variables.items():
        if variable in ("not_these_templates", "readme"):
            continue
        elif variable == "extra_files" and data != "":
            data = "\n\tEXTRA_FILES=\"{}\" \\".format(data)
        elif variable == "bikeshed_indent_size":
            data = str(data)
        elif variable == "bikeshed_max_line_length" and data != "":
            data = "\nmax_line_length = {}".format(data)
        elif variable == "build_with_node" and data != "":
            data = """
    - uses: actions/setup-node@v4
      with:
        node-version: 20
    - run: npm install"""
        elif variable == "post_build_step" and data != "":
            data = "\n\tPOST_BUILD_STEP='{}' \\".format(data)
        elif variable == ".gitignore":
            output = ""
            for entry in data:
                output += "\n{}".format(entry)
            data = output
        elif variable == "extra_implementers":
            output = ""
            for entry in data:
                output += "\n   * {}: …".format(entry)
            data = output
        elif variable == "html-aam":
            output = ""
            if data:
                output = "\n- [ ] Corresponding [HTML AAM](https://w3c.github.io/html-aam/) issue or PR:"
            data = output
        contents = contents.replace("@@{}@@".format(variable), data)
    return contents


def update_files(shortname, name, in_main=False):
    os.chdir("../{}".format(shortname))

    variables = {
        "source": "source",
        "shortname": shortname,
        "h1": name,
        "extra_files": "",
        "bikeshed_indent_size": 1,
        "bikeshed_max_line_length": "",
        "build_with_node": "",
        "post_build_step": "",
        ".gitignore": [],
        "not_these_templates": None,
        "extra_implementers": [],
        "html-aam": False,
        "readme": None
    }
    if shortname in FACTORY_DB:
        variables.update(FACTORY_DB[shortname])


    # HTML does not use Bikeshed (yet). We do want some output for comparison purposes
    if variables["shortname"] != "html":
        [bs_file] = find_files_with_extension(".bs", recurse=False)
        bs = bs_file[:-len(".bs")]
        variables["bs"] = bs
        variables["source"] = bs + ".bs"

    files = copy_and_fill_templates(variables)

    if in_main:
        subprocess.run(["git", "checkout", "main"], capture_output=True)
        subprocess.run(["git", "pull"], capture_output=True)

    for file in files:
        if variables["not_these_templates"] and file in variables["not_these_templates"]:
            continue
        write_file(file, files[file])
    for file in OBSOLETE_FILES:
        if os.path.isfile(file):
            os.remove(file)

    os.chdir(".")


def create_pr(shortname):
    os.chdir("../{}".format(shortname))

    subprocess.run(["git", "add", "-A"], capture_output=True)
    if b"Changes to be committed" in subprocess.run(["git", "status"], capture_output=True).stdout:
        branch = "meta-template/{}".format(uuid.uuid1())
        subprocess.run(["git", "checkout", "-b", branch], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Meta: update repository files\n\nSee https://github.com/whatwg/spec-factory for details."], capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", branch], capture_output=True)
        subprocess.run(["gh", "pr", "create", "-f"])

    os.chdir(".")


def update_all_standards(create_prs = False):
    for workstream in DB["workstreams"]:
        for standard in workstream["standards"]:
            shortname = href_to_shortname(standard["href"])

            update_files(shortname, standard["name"], True)

            if create_prs:
                 create_pr(shortname)


def main():
    global TEMPLATES, FACTORY_DB, TEMPLATE_PARTS

    TEMPLATES = gather_files(".template")
    FACTORY_DB = json.loads(read_file("factory.json"))
    TEMPLATE_PARTS = gather_files(".template-part")

    parser = argparse.ArgumentParser()
    parser.add_argument("--single", nargs=2, type=str, metavar=("<shortname>", "<h1>"), help="generate a single standard, e.g., --single xhr XMLHttpRequest")
    parser.add_argument("--all", action="store_true", help="generate all standards (as per SG's db.json)")
    parser.add_argument("--create-prs", action="store_true", help="create PRs; can only be used in combination with --all")
    args = parser.parse_args()

    if args.single and not args.create_prs:
        update_files(args.single[0], args.single[1])
    elif args.all:
        update_all_standards(args.create_prs)
    else:
        parser.print_help()
        exit(1)
    exit(0)

main()
