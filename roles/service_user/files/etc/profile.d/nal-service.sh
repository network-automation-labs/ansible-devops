if [ -d /run/user/$UID ] ; then
	export XDG_RUNTIME_DIR=/run/user/$UID
	export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/podman/podman.sock
fi
