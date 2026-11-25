import unittest
from ai_planner import validate,context
class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.tasks=[dict(id="a",title="Existing",description="Test",status="complete",parent=None)]
    def test_duplicates(self):
        self.assertEqual(validate({"tasks":[dict(title=" EXISTING ",description="Test",parent=None)]},self.tasks),[])
    def test_valid(self):
        self.assertEqual(len(validate({"tasks":[dict(title="Replication",description="Reproduce",parent="a")]},self.tasks)),1)
    def test_bad_parent(self):
        with self.assertRaises(ValueError): validate({"tasks":[dict(title="New",description="Test",parent="other")]},self.tasks)
    def test_limit(self):
        with self.assertRaises(ValueError): validate({"tasks":[{}]*6},self.tasks)
    def test_context(self):
        c=context(dict(title="Project",description="Scope",criteria="Evidence"),self.tasks,[dict(task="a",status="accepted",summary="Finding",review="Reviewed",evidence="not sent")])
        self.assertNotIn("evidence",c["findings"][0])
