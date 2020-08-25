#!/bin/sh

# set -x
set -e
set -u

BRANCH_NAME=${1:=-}

git submodule foreach 'git fetch origin master && git checkout FETCH_HEAD'
git submodule status

(
for updated_submodule in $(git submodule status | grep -E '^\+' | cut -d' ' -f2); do
    echo "I: Submodule upadted ${updated_submodule}" > /dev/stderr
    git add ${updated_submodule}
    git submodule summary ${updated_submodule}
done
) > .submodule-summary

if [ -z "$(git diff --cached)" ]; then
    echo "I: No changes"
    exit 0
fi

echo "I: Changes summary" > /dev/stderr
cat .submodule-summary > /dev/stderr

(
    echo "Update submodules"
    echo
    cat .submodule-summary
) | git commit -F -

git log HEAD^!

if [ -n "${BRANCH_NAME}" ]; then
    git push origin HEAD:refs/heads/${BRANCH_NAME}
fi
