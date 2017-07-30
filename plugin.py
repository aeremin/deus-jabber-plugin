from collections import namedtuple
import re


StatusParsed = namedtuple('StatusParsed', ['target', 'proxy_level'])
LookParsed = namedtuple('StatusParsed', [
                        'node', 'program', 'node_type', 'disabled_for', 'node_effect', 'childs'])
ProgramInfoParsed = namedtuple('StatusParsed', [
                               'program', 'effect', 'inevitable_effect', 'node_types', 'duration'])
AttackParsed = namedtuple(
    'StatusParsed', ['attack_program', 'defense_program', 'success'])
DonCareParsed = namedtuple('DonCareParsed', [])


def ParseIncomingMessage(msg):
    m = re.search('Current target: (.*)\n'
                  '.*\n'
                  'Proxy level: (\d+)',
                  msg, re.MULTILINE)
    if m:
        target = m.group(1)
        if target == 'not set':
            target = None
        return StatusParsed(target, int(m.group(2)))

    m = re.search('Node ".*/(.*)" properties:\n'
                  'Installed program: (#(\d+)|\*encrypted\*)\n'
                  'Type: (.*)\n',
                  msg, re.MULTILINE)
    if m:
        node = m.group(1)
        program = None
        if m.group(3):
            program = int(m.group(3))
        node_type = m.group(4)
        effect = None
        mm = re.search('Node effect: (.*)\n', msg, re.MULTILINE)
        if mm:
            effect = mm.group(1)

        disabled_for = None
        mm = re.search('DISABLED for: (\d*) sec\n', msg, re.MULTILINE)
        if mm:
            disabled_for = int(mm.group(1))

        child_nodes = []
        mm = re.search('Child nodes:\n(.*)\n\n', msg,
                       re.MULTILINE and re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                mmm = re.match(
                    '\d*: ([a-zA-Z0-9_]*) \(([a-zA-Z0-9 ]*)\): (#(\d*)|\*encrypted\*)', line)
                child_program = None
                if mmm.group(4):
                    child_program = int(mmm.group(4))
                child_nodes.append((mmm.group(1), mmm.group(2), child_program))

        return LookParsed(node, program, node_type, disabled_for, effect, child_nodes)

    m = re.search('#(\d*) progra(m|mm) info:\n'
                  'Effect: ([a-zA-Z0-9_]*)\n',
                  msg, re.MULTILINE)
    if m:
        program = int(m.group(1))
        effect = m.group(3)
        inevitable_effect = None
        mm = re.search(
            'Inevitable effect: ([a-zA-Z0-9_]*)\n', msg, re.MULTILINE)
        if mm:
            inevitable_effect = mm.group(1)
        node_types = []
        mm = re.search('Allowed node types:\n(.*)',
                       msg, re.MULTILINE and re.DOTALL)
        if mm:
            for line in mm.group(1).splitlines():
                mmm = re.match(' -(.*)', line)
                if mmm:
                    node_types.append(mmm.group(1))
        duration = None
        mm = re.search('Duration: (\d*)(sec| sec)', msg, re.MULTILINE)
        if mm:
            duration = int(mm.group(1))
        return ProgramInfoParsed(program, effect, inevitable_effect, node_types, duration)

    m = re.search('(E|e)xecuting progra(m|mm) #(\d*).*\n'
                  '(.*\n)*'
                  'Node defence: #(\d*)\n'
                  '(.*\n)*'
                  '(A|a)ttack (.*)\n',
                  msg, re.MULTILINE)
    if m:
        return AttackParsed(int(m.group(3)),  int(m.group(5)), m.group(8) == 'successfull')

    if (msg in ['ok', '403 Forbidden'] or
        re.search('Info about .* effect:', msg, re.MULTILINE) or
        re.search('not available(| )\n', msg, re.MULTILINE) or
        re.search('Error 406: node disabled', msg, re.MULTILINE) or
        re.search('network scan started: ', msg, re.MULTILINE)):
        return DonCareParsed()

    return None


Context = namedtuple('Context', ['current_system', 'proxy_level'])

Context = namedtuple('Context', ['current_system', 'proxy_level'])
context = Context(None, None)

last_command = None


def prof_pre_chat_message_display(barejid, resource, message):
    parsed = ParseIncomingMessage(message)
    if isinstance(parsed, StatusParsed):
        context = Context(current_system=parsed.target,
                          proxy_level=parsed.proxy_level)

    if isinstance(parsed, LookParsed):
        pass

    if isinstance(parsed, DonCareParsed):
        return

    if not parsed:
        print('<---')
        print(message)
        print('--->')


def prof_pre_chat_message_send(barejid, message):
    last_command = message
    return None
