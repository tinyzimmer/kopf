import logging
from typing import Optional

import pykube
import requests
import urllib3.exceptions

logger = logging.getLogger(__name__)

# Set in login(), consumed in get_pykube_cfg() and all API calls.
_pykube_cfg: Optional[pykube.KubeConfig] = None


class LoginError(Exception):
    """ Raised when the operator cannot login to the API. """


class AccessError(Exception):
    """ Raised when the operator cannot access the cluster API. """


def login(verify: bool = False) -> None:
    """
    Login to Kubernetes cluster, locally or remotely.

    Keep the logged in state or config object in the global variables,
    so that it can be available for future calls via the same function call.

    Automatic refresh/reload of the tokens or objects also should be done here.
    """

    # Pykube login is mandatory. If it fails, the framework will not run at all.
    try:
        import pykube as _  # noqa: F401  pylint: disable=import-outside-toplevel
    except ImportError:
        pass
    else:
        login_pykube(verify=verify)

    # We keep the official client library auto-login only because it was
    # an implied behavior before switching to pykube -- to keep it so (implied).
    try:
        import kubernetes  # noqa: F401  pylint: disable=import-outside-toplevel
    except ImportError:
        pass
    else:
        login_client(verify=verify)


def login_pykube(verify: bool = False) -> None:
    global _pykube_cfg  # pylint: disable=global-statement
    try:
        _pykube_cfg = pykube.KubeConfig.from_service_account()
        logger.debug("Pykube is configured in cluster with service account.")
    except FileNotFoundError:
        try:
            _pykube_cfg = pykube.KubeConfig.from_file()
            logger.debug("Pykube is configured via kubeconfig file.")
        except (pykube.PyKubeError, FileNotFoundError):
            raise LoginError(f"Cannot authenticate pykube neither in-cluster, nor via kubeconfig.")

    if verify:
        verify_pykube()


def login_client(verify: bool = False) -> None:
    import kubernetes.client  # pylint: disable=import-outside-toplevel
    try:
        kubernetes.config.load_incluster_config()  # cluster env vars
        logger.debug("Client is configured in cluster with service account.")
    except kubernetes.config.ConfigException:
        try:
            kubernetes.config.load_kube_config()  # developer's config files
            logger.debug("Client is configured via kubeconfig file.")
        except kubernetes.config.ConfigException:
            raise LoginError(f"Cannot authenticate client neither in-cluster, nor via kubeconfig.")

    if verify:
        verify_client()


def verify_pykube() -> None:
    """
    Verify if login has succeeded, and the access configuration is still valid.

    All other errors (e.g. 403, 404) are ignored: it means, the host and port
    are configured and are reachable, the authentication token is accepted,
    and the rest are authorization or configuration errors (not a showstopper).
    """
    try:
        api = get_pykube_api()
        rsp = api.get(version="", base="/")
        rsp.raise_for_status()
        api.raise_for_status(rsp)  # replaces requests's HTTPError with its own.
    except requests.exceptions.ConnectionError:
        raise AccessError("Cannot connect to the Kubernetes API. "
                          "Please configure the cluster access.")
    except pykube.exceptions.HTTPError as e:
        if e.code == 401:
            raise AccessError("Cannot authenticate to the Kubernetes API. "
                              "Please login or configure the tokens.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise AccessError("Cannot authenticate to the Kubernetes API. "
                              "Please login or configure the tokens.")


def verify_client() -> None:
    """
    Verify if login has succeeded, and the access configuration is still valid.

    All other errors (e.g. 403, 404) are ignored: it means, the host and port
    are configured and are reachable, the authentication token is accepted,
    and the rest are authorization or configuration errors (not a showstopper).
    """
    import kubernetes.client.rest  # pylint: disable=import-outside-toplevel
    try:
        api = kubernetes.client.CoreApi()
        api.get_api_versions()
    except urllib3.exceptions.HTTPError:
        raise AccessError("Cannot connect to the Kubernetes API. "
                          "Please configure the cluster access.")
    except kubernetes.client.rest.ApiException as e:
        if e.status == 401:
            raise AccessError("Cannot authenticate to the Kubernetes API. "
                              "Please login or configure the tokens.")


def get_pykube_cfg() -> pykube.KubeConfig:
    if _pykube_cfg is None:
        raise LoginError("Not logged in with PyKube.")
    return _pykube_cfg


# TODO: add some caching, but keep kwargs in mind. Maybe add a key= for purpose/use-place?
def get_pykube_api(
        timeout: Optional[float] = None,
) -> pykube.HTTPClient:
    kwargs = dict(timeout=timeout)
    return pykube.HTTPClient(get_pykube_cfg(), **kwargs)
