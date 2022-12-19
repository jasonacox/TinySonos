docker run \
-d \
-p 8001:8001 \
-p 54000:54000 \
-p 1900:1900/udp \
-e MEDIAPATH='/media' \
-e DROPPREFIX='/media' \
-v /Volumes/Plex:/media:ro \
--name tinysonos \
--user ${UID} \
--restart unless-stopped \
jasonacox/tinysonos
