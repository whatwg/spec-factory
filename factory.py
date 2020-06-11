#!/usr/bin/env python3

import os, subprocess, uuid, json, requests

OBSOLETE_FILES = [".travis.yml", "deploy_key.enc"]

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
        elif variable == "post_build_step" and data != "":
            data = "\n\tPOST_BUILD_STEP='{}' \\".format(data)
        elif variable == ".gitignore":
            output = ""
            for entry in data:
                output += "\n{}".format(entry)
            data = output
        contents = contents.replace("@@{}@@".format(variable), data)
    return contents


def update(templates, variables):
    os.chdir("../{}".format(variables["shortname"]))

    # HTML does not use Bikeshed (yet). We do want some output for comparison purposes
    if variables["shortname"] != "html":
        [bs_file] = find_files_with_extension(".bs", recurse=False)
        bs = bs_file[:-len(".bs")]
        variables["bs"] = bs

    files = fill_templates(templates, variables)

    subprocess.run(["git", "checkout", "master"], capture_output=True)
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

    subprocess.run(["git", "add", "-A"], capture_output=True)
    if b"Changes to be committed" in subprocess.run(["git", "status"], capture_output=True).stdout:
        subprocess.run(["git", "checkout", "-b", "meta-template/{}".format(uuid.uuid1())], capture_output=True)
        subprocess.run(["git", "commit", "-m", "Meta: update repository files\n\nSee https://github.com/whatwg/spec-factory for details."], capture_output=True)
        subprocess.run(["gh", "pr", "create", "-f"])
    os.chdir(".")


def main():
    templates = gather_templates()
    db = json.loads(requests.get("https://github.com/whatwg/sg/raw/master/db.json").text)
    local_db = json.loads(read_file("factory.json"))
    for workstream in db["workstreams"]:
        for standard in workstream["standards"]:
            shortname = href_to_shortname(standard["href"])
            # Don't update repos we don't yet support
            # https://github.com/whatwg/spec-factory/issues/1
            if shortname == "streams":
                continue
            variables = {
                "shortname": shortname,
                "h1": standard["name"],
                "extra_files": "",
                "post_build_step": "",
                ".gitignore": [],
                "only_these_templates": None,
                "not_these_templates": None
            }
            if shortname in local_db:
                variables.update(local_db[shortname])
            update(templates, variables)

main()
