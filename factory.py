#!/usr/bin/env python

import argparse, os, subprocess, uuid, json, requests

OBSOLETE_FILES = [".travis.yml", "deploy_key.enc"]
TEMPLATES = {}
DB = json.loads(requests.get("https://github.com/whatwg/sg/raw/main/db.json").text)
FACTORY_DB = {}

def read_file(file):
    return open(file, "r", encoding="utf-8").read()

def write_file(file, contents):
    dirs = os.path.dirname(file)
    if dirs:
        os.makedirs(dirs, exist_ok=True)
    open(file, "w", encoding="utf-8").write(contents)

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


def gather_templates():
    templates = {}
    for path in find_files_with_extension(".template"):
        templates[path] = read_file(path)
    return templates


def fill_templates(templates, variables):
    output = {}
    for template in templates:
        output_name = template[:-len(".template")]
        output[output_name] = fill_template(templates[template], variables)
    return output

def fill_template(contents, variables):
    for variable, data in variables.items():
        if variable in ("not_these_templates", "only_these_templates"):
            continue
        elif variable == "extra_files" and data != "":
            data = "\n\tEXTRA_FILES=\"{}\" \\".format(data)
        elif variable == "build_with_node":
            output = ""
            if data:
                output = """
    - uses: actions/setup-node@v2
      with:
        node-version: 14
    - run: npm install"""
            data = output
        elif variable == "post_build_step" and data != "":
            data = "\n\tPOST_BUILD_STEP='{}' \\".format(data)
        elif variable == ".gitignore":
            output = ""
            for entry in data:
                output += "\n{}".format(entry)
            data = output
        elif variable == "extra_implementers":
            data = map(lambda name : "\n   * " + name + ": …", data)
        contents = contents.replace("@@{}@@".format(variable), data)
    return contents


def update_files(shortname, name):
    os.chdir("../{}".format(shortname))

    variables = {
        "shortname": shortname,
        "h1": name,
        "extra_files": "",
        "build_with_node": "",
        "post_build_step": "",
        ".gitignore": [],
        "only_these_templates": None,
        "not_these_templates": None,
        "extra_implementers": []
    }
    if shortname in FACTORY_DB:
        variables.update(FACTORY_DB[shortname])


    # HTML does not use Bikeshed (yet). We do want some output for comparison purposes
    if variables["shortname"] != "html":
        [bs_file] = find_files_with_extension(".bs", recurse=False)
        bs = bs_file[:-len(".bs")]
        variables["bs"] = bs

    files = fill_templates(TEMPLATES, variables)

    subprocess.run(["git", "checkout", "main"], capture_output=True)
    subprocess.run(["git", "pull"], capture_output=True)
    for file in files:
        if variables["only_these_templates"] and file not in variables["only_these_templates"]:
            continue
        elif variables["not_these_templates"] and file in variables["not_these_templates"]:
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


def update_all_standards(create_pr = False):
    for workstream in DB["workstreams"]:
        for standard in workstream["standards"]:
            shortname = href_to_shortname(standard["href"])

            update_files(shortname, standard["name"])

            if create_pr:
                 create_pr(shortname)


def main():
    global TEMPLATES, FACTORY_DB

    TEMPLATES = gather_templates()
    FACTORY_DB = json.loads(read_file("factory.json"))

    parser = argparse.ArgumentParser()
    parser.add_argument("--single", nargs=2, type=str)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--create-prs", action="store_true")
    args = parser.parse_args()

    if args.single:
        update_files(args.single[0], args.single[1])
    elif args.all:
        update_all_standards(args.create_prs)
    else:
        print("Please invoke as one of:\n\n" + \
              "./factory.py --single <shortname> <name>\n" + \
              "./factory.py --all\n" + \
              "./factory.py --all --create-prs")

main()
