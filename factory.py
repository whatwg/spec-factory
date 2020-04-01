#!/usr/bin/env python

import os, subprocess, uuid, json, requests

def read_file(file):
    return open(file, "r", encoding="utf-8").read()

def write_file(file, contents):
    open(file, "w", encoding="utf-8").write(contents)

def href_to_shortname(href):
    return href[len("https://"):href.index(".")]

def find_files_with_extension(extension):
    files = []
    for file in os.listdir("."):
        if os.path.isfile(file) and file.endswith(extension):
            files.append(file)
    return files


def gather_templates():
    templates = {}
    for file in find_files_with_extension(".template"):
        templates[file] = read_file(file)
    return templates


def fill_templates(templates, variables):
    output = {}
    for template in templates:
        output_name = template[:-len(".template")]
        print(output_name)
        output[output_name] = fill_template(templates[template], variables)
    return output

def fill_template(contents, variables):
    for variable, data in variables.items():
        if variable == "extra_files" and data != "":
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
        [bs_file] = find_files_with_extension(".bs")
        bs = bs_file[:-len(".bs")]
        variables["bs"] = bs

    files = fill_templates(templates, variables)

    subprocess.run(["git", "checkout", "master"])
    subprocess.run(["git", "pull"])
    subprocess.run(["git", "checkout", "-b", "meta-template/{}".format(uuid.uuid1())])
    for file in files:
        write_file(file, files[file])
        subprocess.run(["git", "add", file])
    subprocess.run(["git", "commit", "-m", "Meta: update repository files\n\nSee https://github.com/whatwg/spec-factory for details."])

    os.chdir(".")


def main():
    templates = gather_templates()
    db = json.loads(requests.get("https://github.com/whatwg/sg/raw/annevk/db/db.json").text)
    local_db = json.loads(read_file("factory.json"))
    for workstream in db["workstreams"]:
        for standard in workstream["standards"]:
            shortname = href_to_shortname(standard["href"])
            variables = {
                "shortname": shortname,
                "h1": standard["name"],
                "extra_files": "",
                "post_build_step": "",
                ".gitignore": []
            }
            if shortname in local_db:
                variables.update(local_db[shortname])
            update(templates, variables)

main()
