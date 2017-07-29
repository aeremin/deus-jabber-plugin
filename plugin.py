from enum import Enum
import re


class AnswerType(Enum):
    UNKNOWN = 1
    STATUS = 2
    LOOK = 3
    PROGRAM_INFO = 4
    ATTACK = 5


def ParseIncomingMessage(msg):
    m = re.search('Current target: (.*)\n'
                  '.*\n'
                  'Proxy level: (\d+)',
                  msg, re.MULTILINE)
    if m:
        target = m.group(1)
        if target == 'not set':
            target = None
        return AnswerType.STATUS, target, None, int(m.group(2))

    m = re.search('Node "(.*)" properties:\n'
                  'Installed program: #(\d+)\n'
                  'Type: (.*)\n',
                  msg, re.MULTILINE)
    if m:
        node = m.group(1)
        program = int(m.group(2))
        node_type = m.group(3)
        effect = None
        mm = re.search('Node effect: (.*)\n', msg, re.MULTILINE)
        if mm:
            effect = mm.group(1)

        disabled_for = None
        mm = re.search('DISABLED for: (\d*) sec\n', msg, re.MULTILINE)
        if mm:
            disabled_for = int(mm.group(1))

        child_nodes = []
        mm = re.search('Child nodes:\n(.*)\n\n', msg, re.MULTILINE and re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                mmm = re.match('\d*: ([a-zA-Z0-9]*) \(([a-zA-Z0-9 ]*)\): (#(\d*)|\*encrypted\*)', line)
                child_program = None
                if mmm.group(4):
                    child_program = int(mmm.group(4))
                child_nodes.append((mmm.group(1), mmm.group(2), child_program))

        return node, program, node_type, disabled_for, effect, child_nodes

    return None
