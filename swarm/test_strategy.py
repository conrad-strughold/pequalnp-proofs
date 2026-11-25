import unittest
from strategy import propose_tasks,check_evidence
class StrategyTest(unittest.TestCase):
    def test_planning(self):
        p={"description":"Scope","criteria":"Criteria"}
        first=propose_tasks(p,[])
        self.assertEqual(len(first),2)
        existing=[dict(t,id=str(i),status="open") for i,t in enumerate(first)]
        self.assertEqual(propose_tasks(p,existing),[])
        existing[0]["status"]="complete"
        next_tasks=propose_tasks(p,existing)
        self.assertEqual(len(next_tasks),1)
        self.assertEqual(next_tasks[0]["parent"],"0")
    def test_validation(self):
        self.assertFalse(check_evidence("","")["pass"])
        self.assertTrue(check_evidence("Finding","Reproduced")["pass"])
