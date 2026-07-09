# SPDX-License-Identifier: AGPL-3.0-only
#
# The Python configuration structure in this file is licensed as project code.
# Embedded Arknights names, dialogue text, voice references, and asset paths are
# game content and are not re-licensed by this repository. See ASSETS-NOTICE.md.

# Existing character images with the greeting voice.

GREETING = {
    "title": "问候",
    "audio": "assets/voices/char_1052_kalts2/cn_042.mp3",
    "text": "Dr.，我在。",
}


myconfig = {
    "processed_png/1_4_cropped.png": {
        "speaker": "凯尔希·思衡托",
        "side": "left",
        "voices": [GREETING],
    },
    "processed_png/2_4_cropped.png": {
        "speaker": "凯尔希·思衡托",
        "side": "left",
        "voices": [GREETING],
    },
}
