SHELL=/bin/bash -o pipefail
.PHONY: local remote deploy

remote: @@bs@@.bs
	@ (HTTP_STATUS=$$(curl https://api.csswg.org/bikeshed/ \
	                       --output @@bs@@.html \
	                       --write-out "%{http_code}" \
	                       --header "Accept: text/plain, text/html" \
	                       -F die-on=warning \
	                       -F md-Text-Macro="COMMIT-SHA LOCAL COPY" \
	                       -F file=@@@bs@@.bs) && \
	[[ "$$HTTP_STATUS" -eq "200" ]]) || ( \
		echo ""; cat @@bs@@.html; echo ""; \
		rm -f @@bs@@.html; \
		exit 22 \
	);

local: @@bs@@.bs
	bikeshed spec @@bs@@.bs @@bs@@.html --md-Text-Macro="COMMIT-SHA LOCAL COPY"

deploy: @@bs@@.bs
	curl --remote-name --fail https://resources.whatwg.org/build/deploy.sh@@extra_files@@@@post_build_step@@
	bash ./deploy.sh
