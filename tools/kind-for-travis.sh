#!/bin/bash
set -eu
set -x

: ${KUBERNETES_VERSION:=latest}
: ${KIND_VERSION:=latest}

if [[ "${KUBERNETES_VERSION}" == latest ]] ; then
    KUBERNETES_VERSION=$( curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt )
fi

if [[ "${KIND_VERSION}" == latest ]] ; then
    KIND_VERSION=$(
      curl -sI https://github.com/kubernetes-sigs/kind/releases/latest | \
      grep -iE '^Location:' | tr -d '\r\n' | sed -E -e 's@.*/tag/(.*)$@\1@'
    )
fi

curl -Lo kubectl https://storage.googleapis.com/kubernetes-release/release/"${KUBERNETES_VERSION}"/bin/linux/amd64/kubectl
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

curl -Lo kind https://github.com/kubernetes-sigs/kind/releases/download/"${KIND_VERSION}"/kind-$(uname)-amd64
chmod +x kind
sudo mv kind /usr/local/bin/

mkdir -p $HOME/.kube
touch $KUBECONFIG

kind create cluster -v 6 --image kindest/node:"${KUBERNETES_VERSION}"
