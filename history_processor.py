import plugin
import re

with open('example.history', encoding='utf-8') as f:
    for line in f:
        m = re.search('\|.*\|\d\|(from|to)\|N---\|(.*)', line)
        from_or_to = m.group(1)
        msg = m.group(2).replace('\\n', '\n')
        if (from_or_to == 'from'):
            plugin.prof_pre_chat_message_display('', '', msg)
        else:
            plugin.prof_pre_chat_message_send('', msg)

