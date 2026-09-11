
# Goal
A proxy which "translates" jellyfin metadata on the fly using a metadata provider such as imdb

## Core Flow
Proxy goes in between the jellyfin application and your client edge.

1. Request received.
2. determine if request contains metadata to be translated
3. if transfeable forward request with interception. else forward bytes directly via stream.
4. detect content
5. detect user locale
6. fetch metadata language (if locale not default locale)
7. modify response content with the fetched language
8. finish response

### Scope

- Movie metadata
- static config

### Future

- User selectable locale
- Series metadata
- Explore spoofing default audio track based on user locale
