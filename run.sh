docker run \
-d \
--network host \
-e M3UPATH='/media' \
-e MEDIAPATH='/media' \
-e DROPPREFIX='/media' \
-v /media:/media:ro \
--name tinysonos \
--user ${UID} \
--restart unless-stopped \
jasonacox/tinysonos
