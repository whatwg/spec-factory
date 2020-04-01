This repository enables repositories of WHATWG standards to be organized centrally to a certain extent. This is useful for the support files (the files with the `.template` extension), which are often nearly identical and prone to errors.

`factory.py` takes care of updating existing WHATWG standard repositories. It assumes they are in parallel directories using their "shortname" as directory name. `factory.json` supplies data for a exceptional cases.

The HTML and Streams Standards are currently not handled.
