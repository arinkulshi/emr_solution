from hl7_converter import convert_hl7_to_fhir

hl7_msg = """MSH|^~\\&|EPIC|HOSPITAL|EMR|CLINIC|20231031120000||ADT^A04|MSG00001|P|2.5
PID|1||MRN123456^^^MRN||Smith^John^A||19801215|M|||123 Main St^^Boston^MA^02101||555-1234|||S||ACCT123456
IN1|1|PPO123|BC001|BlueCross BlueShield|PO Box 1234^^Boston^MA^02101|||||GRP456789|Gold Plan PPO"""
result = convert_hl7_to_fhir(hl7_msg)
print("Patient:", result["patient"])
print("Coverage:", result["coverage"])