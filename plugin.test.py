import unittest
import plugin


def fun(x):
    return x + 1


class MyTest(unittest.TestCase):
    def testParsesStatusNoTarget(self):
        msg = '''
--------------------
willy220 status:
Current target: not set
Current administrating system: none
Proxy level: 6
Current proxy address: kenguru3362@sydney
END ----------------
        '''
        answer_type, target, administrating_system, proxy_level = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.STATUS)
        self.assertIsNone(target)
        self.assertIsNone(administrating_system)
        self.assertEqual(proxy_level, 6)

    def testParsesStatusWithTarget(self):
        msg = '''
--------------------
willy220 status:
Current target: ManInBlack
Current administrating system: none
Proxy level: 2
Current proxy address: coder5133@mumbai
END ----------------
        '''
        answer_type, target, administrating_system, proxy_level = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.STATUS)
        self.assertEqual(target, 'ManInBlack')
        self.assertIsNone(administrating_system)
        self.assertEqual(proxy_level, 2)

    def testParsesLook(self):
        msg = '''
--------------------
Node "ManInBlack/firewall" properties:
Installed program: #2209900
Type: Firewall
DISABLED for: 440 sec
Child nodes:
0: antivirus1 (Antivirus): #1811628
1: antivirus2 (Antivirus): #16530052 DISABLED

END ----------------
'''
        answer_type, node, program, node_type, disabled_for, node_effect, childs = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.LOOK)
        self.assertEqual(node, 'ManInBlack/firewall')
        self.assertEqual(program, 2209900)
        self.assertEqual(node_type, 'Firewall')
        self.assertEqual(disabled_for, 440)
        self.assertIsNone(node_effect)
        self.assertEqual(childs, [
                         ('antivirus1', 'Antivirus', 1811628), ('antivirus2', 'Antivirus', 16530052)])

    def testParsesLookWithNodeEffect(self):
        msg = '''
--------------------
Node "ManInBlack/VPN1" properties:
Installed program: #6162975
Type: VPN
Node effect: trace
END ----------------
'''
        answer_type, node, program, node_type, disabled_for, node_effect, childs = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.LOOK)
        self.assertEqual(node, 'ManInBlack/VPN1')
        self.assertEqual(program, 6162975)
        self.assertEqual(node_type, 'VPN')
        self.assertIsNone(disabled_for)
        self.assertEqual(node_effect, 'trace')
        self.assertEqual(childs, [])

    def testParsesLookWithEncrypted(self):
        msg = '''
--------------------
Node "BlackMirror944/brandmauer3" properties:
Installed program: #2294523
Type: Brandmauer
DISABLED for: 591 sec
Child nodes:
0: cryptocore3 (Cyptographic system): *encrypted*
1: VPN4 (VPN): #2209900

END ----------------
'''
        answer_type, node, program, node_type, disabled_for, node_effect, childs = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.LOOK)
        self.assertEqual(node, 'BlackMirror944/brandmauer3')
        self.assertEqual(program, 2294523)
        self.assertEqual(node_type, 'Brandmauer')
        self.assertEqual(disabled_for, 591)
        self.assertIsNone(node_effect)
        self.assertEqual(childs, [
                         ('cryptocore3', 'Cyptographic system', None), ('VPN4', 'VPN', 2209900)])

    def testParsesDefenseProgramInfo(self):
        msg = '''
--------------------
#2209900 programm info:
Effect: trace
Inevitable effect: logname
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
END ----------------
'''
        answer_type, program, effect, inevitable_effect, node_types, duration = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.PROGRAM_INFO)
        self.assertEqual(program, 2209900)
        self.assertEqual(effect, 'trace')
        self.assertEqual(inevitable_effect, 'logname')
        self.assertEqual(node_types, ['Firewall', 'Antivirus', 'VPN',
                                      'Brandmauer', 'Router', 'Traffic monitor', 'Cyptographic system'])
        self.assertIsNone(duration)

    def testParsesAttackProgramInfo(self):
        msg = '''
--------------------
#1100 programm info:
Effect: disable
Allowed node types:
 -Firewall
 -Antivirus
 -VPN
 -Brandmauer
 -Router
 -Traffic monitor
 -Cyptographic system
Duration: 600sec.
END ----------------
'''
        answer_type, program, effect, inevitable_effect, node_types, duration = plugin.ParseIncomingMessage(
            msg)
        self.assertEqual(answer_type, plugin.AnswerType.PROGRAM_INFO)
        self.assertEqual(program, 1100)
        self.assertEqual(effect, 'disable')
        self.assertEqual(node_types, ['Firewall', 'Antivirus', 'VPN',
                                      'Brandmauer', 'Router', 'Traffic monitor', 'Cyptographic system'])
        self.assertEqual(duration, 600)


if __name__ == '__main__':
    unittest.main()
