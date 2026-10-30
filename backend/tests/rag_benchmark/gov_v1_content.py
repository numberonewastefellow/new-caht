"""Static content for the gov_v1 RAG benchmark corpus (used by gen_gov_rag_corpus).

Everything here is FICTITIOUS: department orders, GO numbers, names, IDs,
hospitals, colleges and amounts are invented for testing. Domain context comes
from the department briefs in gtm-government/departments/.
"""

from dataclasses import dataclass
from dataclasses import field

DISTRICTS: list[tuple[str, str]] = [
    ("HYD", "Hyderabad"),
    ("RRD", "Ranga Reddy"),
    ("MDL", "Medchal-Malkajgiri"),
    ("WGL", "Warangal"),
    ("KRM", "Karimnagar"),
    ("NLG", "Nalgonda"),
    ("KMM", "Khammam"),
    ("NZB", "Nizamabad"),
    ("ADB", "Adilabad"),
    ("MBN", "Mahabubnagar"),
]
DISTRICT_NAMES = {code: name for code, name in DISTRICTS}
DISTRICT_LOCAL: dict[str, dict[str, str]] = {
    "te": {
        "WGL": "వరంగల్",
        "KRM": "కరీంనగర్",
        "NLG": "నల్గొండ",
        "KMM": "ఖమ్మం",
    },
    "hi": {
        "HYD": "हैदराबाद",
        "RRD": "रंगारेड्डी",
        "NZB": "निज़ामाबाद",
    },
}

FIRST_NAMES = [
    "Ravi",
    "Lakshmi",
    "Srinivas",
    "Padma",
    "Venkatesh",
    "Anitha",
    "Ramesh",
    "Sujatha",
    "Mahesh",
    "Kavitha",
    "Naresh",
    "Swathi",
    "Prakash",
    "Radha",
    "Kiran",
    "Madhavi",
    "Suresh",
    "Jyothi",
    "Anil",
    "Sarala",
    "Vijay",
    "Deepa",
    "Raju",
    "Bhavani",
    "Harish",
    "Usha",
    "Sai",
    "Rekha",
    "Gopal",
    "Shobha",
]
SURNAMES = [
    "Reddy",
    "Rao",
    "Goud",
    "Naidu",
    "Sharma",
    "Varma",
    "Chary",
    "Yadav",
    "Kumar",
    "Devi",
    "Prasad",
    "Murthy",
    "Babu",
    "Patel",
    "Naik",
    "Achari",
]

DISCLAIMER = {
    "en": "SYNTHETIC BENCHMARK DOCUMENT - all names, identifiers, figures and orders "
    "in this document are fictitious and exist only to test search quality.",
    "te": "సింథటిక్ బెంచ్‌మార్క్ పత్రం - ఇందులోని పేర్లు, గుర్తింపు సంఖ్యలు, అంకెలు, "
    "ఉత్తర్వులు అన్నీ కల్పితం; శోధన నాణ్యత పరీక్ష కోసం మాత్రమే.",
    "hi": "सिंथेटिक बेंचमार्क दस्तावेज़ - इसमें सभी नाम, पहचान संख्याएँ, आँकड़े और आदेश "
    "काल्पनिक हैं; केवल खोज गुणवत्ता परीक्षण के लिए।",
}


@dataclass(frozen=True)
class Column:
    name: str
    label: str
    kind: str  # id | district | person | choice | int | date | status
    choices: tuple[str, ...] = ()
    lo: int = 0
    hi: int = 0
    step: int = 1


@dataclass(frozen=True)
class LocalNames:
    name: str
    service: str
    officer: str
    appellate: str
    district: str  # district code of the annex


@dataclass(frozen=True)
class Dept:
    key: str
    code: str
    name: str
    service: str
    officer: str
    appellate: str
    register_title: str
    record_noun: str
    register_cols: tuple[Column, ...]
    csv_slug: str
    csv_title: str
    csv_cols: tuple[Column, ...]
    sop_focus: str
    background: tuple[str, str]
    target_noun: str
    local_lang: str | None = None
    local: LocalNames | None = None
    has_distractor: bool = False
    go_boost: int = 0
    distractor_boost: int = 0
    extra: dict[str, str] = field(default_factory=dict)


def _c(name: str, label: str, kind: str, *choices: str) -> Column:
    return Column(name=name, label=label, kind=kind, choices=tuple(choices))


def _n(name: str, label: str, lo: int, hi: int, step: int = 1) -> Column:
    return Column(name=name, label=label, kind="int", lo=lo, hi=hi, step=step)


STATUS_APP = ("Approved", "Pending", "Rejected", "Query Raised")

DEPTS: list[Dept] = [
    Dept(
        key="land",
        code="LND",
        name="Revenue Department - Land Mutation and Record of Rights",
        service="land mutation",
        officer="Tahsildar",
        appellate="Revenue Divisional Officer",
        register_title="Land Mutation Applications Register 2026",
        record_noun="application",
        register_cols=(
            _c("application_no", "application number", "id"),
            _c("district", "district", "district"),
            _c(
                "village",
                "village",
                "choice",
                "Kondapur",
                "Shamirpet",
                "Ibrahimpatnam",
                "Ghatkesar",
                "Keesara",
                "Hanamkonda",
                "Jangaon",
                "Bhongir",
                "Miryalaguda",
                "Kodad",
            ),
            _c("applicant", "applicant", "person"),
            _c(
                "mutation_type",
                "mutation type",
                "choice",
                "Sale Deed",
                "Gift Deed",
                "Succession",
                "Partition",
                "Court Decree",
            ),
            _n("fee_rs", "mutation fee (Rs)", 500, 5000, 50),
            _n("extent_cents", "extent (cents)", 5, 900),
            _c("status", "status", "status", *STATUS_APP),
            _c("filed_on", "filing date", "date"),
        ),
        csv_slug="pattadar_passbooks",
        csv_title="Pattadar Passbook Issue List 2026",
        csv_cols=(
            _c("passbook_no", "passbook number", "id"),
            _c("pattadar", "pattadar", "person"),
            _c("district", "district", "district"),
            _c(
                "land_class",
                "land class",
                "choice",
                "Patta",
                "Assigned",
                "Inam",
                "Endowment",
            ),
            _n("market_value_rs", "market value (Rs)", 100000, 4500000, 500),
            _c("issued_on", "issue date", "date"),
        ),
        sop_focus="processing a mutation application after a registered transfer",
        background=(
            "Every registered sale, gift, partition or succession must be reflected in "
            "the Record of Rights (1-B) so that the new holder can obtain a pattadar "
            "passbook, crop loans and compensation. Mutation files move from the Village "
            "Revenue Officer to the Revenue Inspector and the Tahsildar, and delays at any "
            "stage leave the record out of step with the registered deed.",
            "A review of last year's files showed that most delays arose from missing "
            "chain-of-title papers, extent mismatches between the deed and the 1-B, and "
            "pending checks against the prohibited-properties list. Government therefore "
            "revises the fee, the disposal timeline and the appeal procedure.",
        ),
        target_noun="mutations",
        local_lang="te",
        local=LocalNames(
            name="రెవెన్యూ (భూ మ్యుటేషన్)",
            service="భూ మ్యుటేషన్",
            officer="తహసీల్దార్",
            appellate="రెవెన్యూ డివిజనల్ అధికారి",
            district="WGL",
        ),
        has_distractor=True,
        distractor_boost=1,
    ),
    Dept(
        key="aarogyasri",
        code="ARG",
        name="Health Department - Aarogyasri Health Care Trust (Pre-Authorization)",
        service="pre-authorization",
        officer="District Coordinator",
        appellate="Chief Medical Auditor of the Trust",
        register_title="Aarogyasri Pre-Authorization Register 2026",
        record_noun="pre-authorization request",
        register_cols=(
            _c("preauth_id", "pre-authorization ID", "id"),
            _c("district", "district", "district"),
            _c(
                "network_hospital",
                "network hospital",
                "choice",
                "Lotus Care Hospital",
                "Godavari General Hospital",
                "Krishna Heart Centre",
                "Deccan Ortho Clinic",
                "Sunrise Childrens Hospital",
                "Kakatiya Medical Centre",
                "Pragati Kidney Care",
            ),
            _c("beneficiary", "beneficiary", "person"),
            _c(
                "specialty",
                "specialty",
                "choice",
                "Cardiology",
                "Orthopaedics",
                "Nephrology",
                "Oncology",
                "Neurosurgery",
                "Paediatrics",
            ),
            _n("package_amount_rs", "package amount (Rs)", 10000, 250000, 500),
            _n("length_of_stay_days", "length of stay (days)", 1, 21),
            _c("status", "status", "status", *STATUS_APP),
            _c("raised_on", "date raised", "date"),
        ),
        csv_slug="claims_settled",
        csv_title="Aarogyasri Claim Settlement List 2026",
        csv_cols=(
            _c("claim_no", "claim number", "id"),
            _c("beneficiary", "beneficiary", "person"),
            _c("district", "district", "district"),
            _c(
                "specialty",
                "specialty",
                "choice",
                "Cardiology",
                "Orthopaedics",
                "Nephrology",
                "Oncology",
                "Neurosurgery",
                "Paediatrics",
            ),
            _n("settled_amount_rs", "settled amount (Rs)", 8000, 240000, 100),
            _c("settled_on", "settlement date", "date"),
        ),
        sop_focus="reviewing an e-preauthorization raised by a network hospital",
        background=(
            "Network hospitals raise e-preauthorizations for cashless treatment of "
            "eligible white-card families. Each request carries the diagnosis, the "
            "proposed package from the procedure master, investigation reports and a cost "
            "estimate, and is reviewed by the pre-authorization wing before treatment.",
            "Audit findings showed repeated queries on incomplete investigation reports "
            "and package codes that did not match the clinical justification. Government "
            "revises the processing charge, review timelines and the appeal route so "
            "that genuine cases are approved faster and the medical auditor's decision "
            "remains final.",
        ),
        target_noun="pre-authorizations",
        local_lang="te",
        local=LocalNames(
            name="ఆరోగ్యశ్రీ ఆరోగ్య ట్రస్ట్",
            service="ముందస్తు అనుమతి (ప్రీ-ఆథరైజేషన్)",
            officer="జిల్లా సమన్వయకర్త",
            appellate="ట్రస్ట్ ముఖ్య వైద్య ఆడిటర్",
            district="KRM",
        ),
        has_distractor=True,
    ),
    Dept(
        key="epass",
        code="EPS",
        name="Social Welfare Department - ePASS Post-Matric Scholarships",
        service="scholarship",
        officer="District Welfare Officer",
        appellate="Director of Social Welfare",
        register_title="ePASS Scholarship Applications Register 2026",
        record_noun="scholarship application",
        register_cols=(
            _c("application_id", "application ID", "id"),
            _c("district", "district", "district"),
            _c(
                "college",
                "college",
                "choice",
                "Govt Degree College Hanamkonda",
                "Govt Junior College Nalgonda",
                "Kakatiya Polytechnic",
                "Govt Degree College Khammam",
                "Model Degree College Karimnagar",
                "Govt Womens College Nizamabad",
            ),
            _c("student", "student", "person"),
            _c(
                "course",
                "course",
                "choice",
                "B.A.",
                "B.Com",
                "B.Sc",
                "B.Tech",
                "Diploma",
                "Intermediate",
            ),
            _n("scholarship_rs", "scholarship amount (Rs)", 5000, 60000, 100),
            _n("attendance_pct", "attendance (%)", 50, 100),
            _c(
                "status",
                "status",
                "status",
                "Sanctioned",
                "Pending",
                "Rejected",
                "Returned for Correction",
            ),
            _c("applied_on", "application date", "date"),
        ),
        csv_slug="disbursements",
        csv_title="Scholarship Disbursement List 2026",
        csv_cols=(
            _c("disbursement_ref", "disbursement reference", "id"),
            _c("student", "student", "person"),
            _c("district", "district", "district"),
            _c(
                "scheme",
                "scheme",
                "choice",
                "Post-Matric",
                "Pre-Matric",
                "Fee Reimbursement",
            ),
            _n("amount_credited_rs", "amount credited (Rs)", 3000, 58000, 100),
            _c("credited_on", "credit date", "date"),
        ),
        sop_focus="verifying and sanctioning a post-matric scholarship application",
        background=(
            "Post-matric scholarships and fee reimbursement are sanctioned through the "
            "ePASS portal after the college principal verifies attendance and the "
            "district welfare office checks income and eligibility. Funds are credited "
            "directly to the student's bank account.",
            "Many applications were returned last year for Aadhaar-bank seeding errors "
            "and attendance below the threshold, and disbursement slipped past the "
            "academic year. Government revises the processing fee, the sanction timeline "
            "and the appeal procedure.",
        ),
        target_noun="sanctions",
        local_lang="te",
        local=LocalNames(
            name="సాంఘిక సంక్షేమం (ఈ-పాస్ ఉపకార వేతనాలు)",
            service="ఉపకార వేతనం",
            officer="జిల్లా సంక్షేమ అధికారి",
            appellate="సాంఘిక సంక్షేమ సంచాలకులు",
            district="NLG",
        ),
        has_distractor=True,
    ),
    Dept(
        key="collectorate",
        code="COL",
        name="District Collectorate - Prajavani Grievances and Certificates",
        service="certificate issuance",
        officer="Additional Collector",
        appellate="District Collector",
        register_title="Prajavani Grievance Petitions Register 2026",
        record_noun="petition",
        register_cols=(
            _c("petition_no", "petition number", "id"),
            _c("district", "district", "district"),
            _c(
                "department",
                "department",
                "choice",
                "Revenue",
                "Panchayat Raj",
                "Civil Supplies",
                "Health",
                "Education",
                "Municipal Administration",
                "Agriculture",
            ),
            _c("petitioner", "petitioner", "person"),
            _c(
                "subject",
                "subject",
                "choice",
                "Pension",
                "Ration Card",
                "Land Record",
                "House Site",
                "Water Supply",
                "Road Repair",
            ),
            _n("days_pending", "days pending", 0, 180),
            _n("hearing_count", "number of hearings", 1, 6),
            _c(
                "status",
                "status",
                "status",
                "Resolved",
                "Pending",
                "Forwarded",
                "Closed",
            ),
            _c("received_on", "date received", "date"),
        ),
        csv_slug="certificates_issued",
        csv_title="Certificates Issued List 2026",
        csv_cols=(
            _c("certificate_no", "certificate number", "id"),
            _c("applicant", "applicant", "person"),
            _c("district", "district", "district"),
            _c(
                "certificate_type",
                "certificate type",
                "choice",
                "Income",
                "Residence",
                "Family Member",
                "Solvency",
                "No-Objection",
            ),
            _n("fee_paid_rs", "fee paid (Rs)", 10, 500, 5),
            _c("issued_on", "issue date", "date"),
        ),
        sop_focus="handling a Prajavani petition and issuing certificates",
        background=(
            "The weekly Prajavani grievance day lets citizens petition the Collector "
            "directly. Petitions are registered, forwarded to the line department, and "
            "tracked until a speaking reply is given. The same office issues income, "
            "residence and family-member certificates.",
            "Coordination reviews found that forwarded petitions often went unanswered "
            "beyond the prescribed time and that certificate requests were processed "
            "without a fixed timeline. Government revises the certificate fee, the "
            "disposal timeline and the appeal procedure.",
        ),
        target_noun="petitions resolved",
        local_lang="te",
        local=LocalNames(
            name="జిల్లా కలెక్టరేట్ (ప్రజావాణి)",
            service="ధృవీకరణ పత్రాల జారీ",
            officer="అదనపు కలెక్టర్",
            appellate="జిల్లా కలెక్టర్",
            district="KMM",
        ),
    ),
    Dept(
        key="cybercrime",
        code="CYB",
        name="Cyber Security Bureau - Cyber Crime Complaints",
        service="cyber fraud complaint",
        officer="Cyber Crime Inspector",
        appellate="Superintendent of Police (Cyber)",
        register_title="Cyber Crime Complaints Register 2026",
        record_noun="complaint",
        register_cols=(
            _c("complaint_id", "complaint ID", "id"),
            _c("district", "district", "district"),
            _c(
                "channel",
                "channel",
                "choice",
                "UPI",
                "Phone Call",
                "Social Media",
                "Email",
                "Fake Website",
                "SMS Link",
            ),
            _c("complainant", "complainant", "person"),
            _c(
                "fraud_type",
                "fraud type",
                "choice",
                "Investment Scam",
                "Loan App",
                "KYC Update",
                "OTP Fraud",
                "Job Offer",
                "Online Shopping",
            ),
            _n("amount_lost_rs", "amount lost (Rs)", 1000, 900000, 10),
            _n("hours_to_report", "hours to report", 1, 240),
            _c(
                "status",
                "status",
                "status",
                "FIR Registered",
                "Under Investigation",
                "Amount Frozen",
                "Closed",
            ),
            _c("reported_on", "date reported", "date"),
        ),
        csv_slug="victim_refunds",
        csv_title="Cyber Fraud Victim Refund List 2026",
        csv_cols=(
            _c("refund_order_no", "refund order number", "id"),
            _c("victim", "victim", "person"),
            _c("district", "district", "district"),
            _c(
                "channel",
                "channel",
                "choice",
                "UPI",
                "Phone Call",
                "Social Media",
                "Email",
                "Fake Website",
                "SMS Link",
            ),
            _n("refund_amount_rs", "refund amount (Rs)", 500, 600000, 10),
            _c("refunded_on", "refund date", "date"),
        ),
        sop_focus="registering a cyber fraud complaint and freezing the money trail",
        background=(
            "Victims of online financial fraud report through the national helpline or "
            "the cyber crime portal. The first hours decide whether the money trail can "
            "be frozen, so complaints are registered, the beneficiary accounts are "
            "flagged with banks and the case is assigned to an investigating officer.",
            "A review found that complaints reported late and incomplete transaction "
            "details were the main reasons for unrecovered amounts. Government revises "
            "the processing charge, response timelines and the appeal procedure.",
        ),
        target_noun="complaints closed",
        local_lang="hi",
        local=LocalNames(
            name="साइबर अपराध ब्यूरो",
            service="साइबर धोखाधड़ी शिकायत",
            officer="साइबर अपराध निरीक्षक",
            appellate="पुलिस अधीक्षक (साइबर)",
            district="HYD",
        ),
        has_distractor=True,
    ),
    Dept(
        key="cid",
        code="EOW",
        name="CID - Economic Offences Wing",
        service="economic offence investigation",
        officer="Deputy Superintendent of Police",
        appellate="Additional Director General of Police (CID)",
        register_title="Economic Offences Case Register 2026",
        record_noun="case",
        register_cols=(
            _c("case_no", "case number", "id"),
            _c("district", "district", "district"),
            _c(
                "scheme_type",
                "scheme type",
                "choice",
                "Chit Fund",
                "Ponzi Deposit",
                "MLM",
                "Real Estate Plot",
                "Gold Scheme",
                "Crypto Token",
            ),
            _c("accused_entity", "accused entity", "person"),
            _c(
                "investigation_stage",
                "investigation stage",
                "choice",
                "Preliminary Enquiry",
                "FIR",
                "Attachment",
                "Chargesheet",
                "Trial",
            ),
            _n("amount_involved_rs", "amount involved (Rs)", 500000, 90000000, 1000),
            _n("victims", "number of victims", 5, 4000),
            _c("status", "status", "status", "Open", "Closed", "Transferred"),
            _c("registered_on", "registration date", "date"),
        ),
        csv_slug="attached_properties",
        csv_title="Attached Property List 2026",
        csv_cols=(
            _c("attachment_order_no", "attachment order number", "id"),
            _c("owner", "owner", "person"),
            _c("district", "district", "district"),
            _c(
                "property_type",
                "property type",
                "choice",
                "House",
                "Plot",
                "Vehicle",
                "Bank Deposit",
                "Gold",
            ),
            _n("attached_value_rs", "attached value (Rs)", 50000, 25000000, 1000),
            _c("attached_on", "attachment date", "date"),
        ),
        sop_focus="investigating a deposit or chit fund fraud and attaching assets",
        background=(
            "The Economic Offences Wing investigates chit fund, deposit and multi-level "
            "marketing frauds that affect many depositors at once. Investigations trace "
            "the money, attach properties under the depositor protection law and file "
            "chargesheets before the designated court.",
            "Cases with thousands of victims stalled for want of forensic audit reports "
            "and delayed attachment orders. Government revises the processing charge, "
            "investigation timelines and the appeal procedure.",
        ),
        target_noun="cases charge-sheeted",
        local_lang="hi",
        local=LocalNames(
            name="सीआईडी आर्थिक अपराध शाखा",
            service="आर्थिक अपराध जाँच",
            officer="उप पुलिस अधीक्षक",
            appellate="अतिरिक्त पुलिस महानिदेशक (सीआईडी)",
            district="RRD",
        ),
        has_distractor=True,
        go_boost=2,
    ),
    Dept(
        key="police",
        code="PCS",
        name="State Police - Chargesheet Cell",
        service="chargesheet filing",
        officer="Station House Officer",
        appellate="Superintendent of Police",
        register_title="FIR and Chargesheet Status Register 2026",
        record_noun="FIR",
        register_cols=(
            _c("fir_no", "FIR number", "id"),
            _c("district", "district", "district"),
            _c(
                "police_station",
                "police station",
                "choice",
                "Town I PS",
                "Town II PS",
                "Rural PS",
                "Central PS",
                "North PS",
                "South PS",
            ),
            _c("investigating_officer", "investigating officer", "person"),
            _c(
                "offence",
                "offence",
                "choice",
                "Theft",
                "Cheating",
                "Assault",
                "House Breaking",
                "Chain Snatching",
                "Road Accident",
            ),
            _n("days_since_fir", "days since FIR", 1, 400),
            _n("witnesses", "number of witnesses", 1, 25),
            _c(
                "status",
                "status",
                "status",
                "Chargesheet Filed",
                "Under Investigation",
                "Final Report",
                "Pending Forensic",
            ),
            _c("registered_on", "registration date", "date"),
        ),
        csv_slug="chargesheets_filed",
        csv_title="Chargesheet Filing List 2026",
        csv_cols=(
            _c("chargesheet_no", "chargesheet number", "id"),
            _c("accused", "accused", "person"),
            _c("district", "district", "district"),
            _c(
                "offence",
                "offence",
                "choice",
                "Theft",
                "Cheating",
                "Assault",
                "House Breaking",
                "Chain Snatching",
                "Road Accident",
            ),
            _n("property_recovered_rs", "property recovered (Rs)", 0, 800000, 50),
            _c("filed_on", "filing date", "date"),
        ),
        sop_focus="completing an investigation and filing the chargesheet",
        background=(
            "After an FIR is registered, the investigating officer collects evidence, "
            "records witness statements, obtains forensic and medical reports and files "
            "the final report or chargesheet before the magistrate within the statutory "
            "period.",
            "A district review found many chargesheets returned for missing forensic "
            "reports and incomplete witness lists, and cases crossing the statutory "
            "period. Government revises the processing charge, timelines and the appeal "
            "procedure.",
        ),
        target_noun="chargesheets",
        local_lang="hi",
        local=LocalNames(
            name="राज्य पुलिस (आरोप-पत्र प्रकोष्ठ)",
            service="आरोप-पत्र दाखिल",
            officer="थाना प्रभारी",
            appellate="पुलिस अधीक्षक",
            district="NZB",
        ),
        has_distractor=True,
    ),
    Dept(
        key="prosecutions",
        code="DOP",
        name="Directorate of Prosecutions",
        service="legal opinion",
        officer="Deputy Director of Prosecutions",
        appellate="Director of Prosecutions",
        register_title="Prosecution Case Tracking Register 2026",
        record_noun="case",
        register_cols=(
            _c("case_ref", "case reference", "id"),
            _c("district", "district", "district"),
            _c(
                "court",
                "court",
                "choice",
                "Principal District Court",
                "I Additional District Court",
                "Chief Judicial Magistrate",
                "Junior Civil Judge",
                "Sessions Court",
                "Special Court (NDPS)",
            ),
            _c("app_assigned", "Assistant Public Prosecutor", "person"),
            _c(
                "offence_category",
                "offence category",
                "choice",
                "Property Offence",
                "Bodily Offence",
                "NDPS",
                "Economic Offence",
                "Cyber Offence",
            ),
            _n("hearing_count", "number of hearings", 1, 60),
            _n("witnesses_examined", "witnesses examined", 0, 30),
            _c(
                "status",
                "status",
                "status",
                "Trial",
                "Judgment Reserved",
                "Convicted",
                "Acquitted",
                "Adjourned",
            ),
            _c("next_hearing", "next hearing date", "date"),
        ),
        csv_slug="legal_opinions",
        csv_title="Legal Opinions Issued List 2026",
        csv_cols=(
            _c("opinion_no", "opinion number", "id"),
            _c("prosecutor", "prosecutor", "person"),
            _c("district", "district", "district"),
            _c(
                "offence_category",
                "offence category",
                "choice",
                "Property Offence",
                "Bodily Offence",
                "NDPS",
                "Economic Offence",
                "Cyber Offence",
            ),
            _n("days_to_opinion", "days taken for opinion", 1, 30),
            _c("issued_on", "issue date", "date"),
        ),
        sop_focus="scrutinising a chargesheet and giving a legal opinion",
        background=(
            "Public prosecutors scrutinise chargesheets before they are filed, advise "
            "investigating officers on gaps in evidence, and conduct the trial. The "
            "Directorate monitors conviction rates, adjournments and the time taken to "
            "give legal opinions.",
            "Opinions were often delayed for want of case diaries and forensic reports, "
            "and appeals against acquittals were filed late. Government revises the "
            "processing charge, opinion timelines and the appeal procedure.",
        ),
        target_noun="opinions",
        has_distractor=True,
    ),
    Dept(
        key="registry",
        code="HCR",
        name="High Court Registry - Filing and Scrutiny",
        service="case filing scrutiny",
        officer="Deputy Registrar (Judicial)",
        appellate="Registrar General",
        register_title="High Court Filing Register 2026",
        record_noun="filing",
        register_cols=(
            _c("filing_no", "filing number", "id"),
            _c("district", "district", "district"),
            _c(
                "case_type",
                "case type",
                "choice",
                "Writ Petition",
                "Civil Revision",
                "Criminal Petition",
                "Second Appeal",
                "Contempt Case",
                "Writ Appeal",
            ),
            _c("petitioner", "petitioner", "person"),
            _c(
                "subject_category",
                "subject category",
                "choice",
                "Service",
                "Land Acquisition",
                "Taxation",
                "Education",
                "Municipal",
                "Excise",
            ),
            _n("court_fee_rs", "court fee (Rs)", 100, 25000, 10),
            _n("defects_found", "defects found", 0, 8),
            _c(
                "status",
                "status",
                "status",
                "Numbered",
                "Defective",
                "Returned",
                "Listed",
            ),
            _c("filed_on", "filing date", "date"),
        ),
        csv_slug="certified_copies",
        csv_title="Certified Copy Issue List 2026",
        csv_cols=(
            _c("copy_application_no", "copy application number", "id"),
            _c("applicant", "applicant", "person"),
            _c("district", "district", "district"),
            _c(
                "case_type",
                "case type",
                "choice",
                "Writ Petition",
                "Civil Revision",
                "Criminal Petition",
                "Second Appeal",
                "Contempt Case",
                "Writ Appeal",
            ),
            _n("copy_fee_rs", "copy fee (Rs)", 20, 3000, 5),
            _c("issued_on", "issue date", "date"),
        ),
        sop_focus="scrutinising a fresh filing and curing defects",
        background=(
            "Fresh filings are scrutinised by the Registry for court fee, annexures, "
            "vakalat and limitation before they are numbered and listed. Defective "
            "filings are returned with a defect memo and must be re-presented.",
            "Defect memos were issued in a large share of filings and re-presentation "
            "often took weeks. Government revises the scrutiny charge, timelines and the "
            "appeal procedure.",
        ),
        target_noun="filings numbered",
        has_distractor=True,
        go_boost=2,
    ),
]
DEPTS_BY_KEY = {d.key: d for d in DEPTS}

# --- GO / SOP templates -------------------------------------------------------

GO_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "govt": "Government of the State (Fictitious) - {dept_name}",
        "title": "Government Order {go_no}, dated {go_date}",
        "subject": "Subject: {service} services - fees, timelines and implementation "
        "guidelines - orders issued.",
        "read": "Read: {ref}",
        "read_none": "Read: Proposals of the Head of Department, dated {prev_date}.",
        "order_heading": "ORDER",
        "o1": "The processing fee for a {service} application is fixed at Rs {fee}.",
        "o2": "Every {service} application shall be disposed of within {days} working days "
        "of receipt.",
        "o3": "Where the timeline is exceeded, a penalty of Rs {penalty} per day of delay "
        "shall be recovered from the officer responsible.",
        "o4": "The {officer} may approve cases of a value up to Rs {ceiling} without "
        "further reference.",
        "o5": "An applicant aggrieved by the decision may appeal to the {appellate} within "
        "{appeal_days} days.",
        "o6": "These orders come into force from {effective}.",
        "table_heading": "District-wise sanctioned posts and allocation",
        "col_district": "District",
        "col_target": "Sanctioned posts",
        "col_alloc": "Allocation (Rs lakh)",
        "monitoring": "District Collectors shall review progress every month and send a "
        "report to the Head of Department. The status of every application shall be "
        "visible to citizens on the online portal, and the reasons for any rejection "
        "shall be recorded in writing.",
        "grievance": "A grievance register shall be maintained in every office. "
        "Grievances shall be acknowledged on the day of receipt and answered in "
        "writing.",
        "supersedes": "This order supersedes {old_go_no}.",
        "signoff": "By order and in the name of the Governor, Principal Secretary to "
        "Government (fictitious).",
    },
    "te": {
        "govt": "రాష్ట్ర ప్రభుత్వం (కల్పితం) - {dept_name}",
        "title": "ప్రభుత్వ ఉత్తర్వు సంఖ్య {go_no}, తేదీ {go_date}",
        "subject": "విషయం: {service} సేవలు - రుసుములు, కాలపరిమితులు మరియు అమలు "
        "మార్గదర్శకాలు - ఉత్తర్వులు జారీ.",
        "read": "చదవండి: {ref}",
        "read_none": "చదవండి: శాఖాధిపతి ప్రతిపాదనలు, తేదీ {prev_date}.",
        "background": "{dept_name} ద్వారా అందించే {service} సేవలను పారదర్శకంగా, నిర్ణీత "
        "కాలపరిమితిలో పౌరులకు అందించడం ప్రభుత్వ లక్ష్యం. గత సంవత్సరం దరఖాస్తుల సంఖ్య "
        "గణనీయంగా పెరగడంతో జిల్లా స్థాయిలో పెండింగ్ కేసులు ఎక్కువయ్యాయి. ఈ నేపథ్యంలో "
        "రుసుములు, కాలపరిమితులు మరియు అప్పీలు విధానాన్ని సవరిస్తూ ఈ క్రింది ఉత్తర్వులు "
        "జారీ చేయడమైనది.",
        "order_heading": "ఉత్తర్వులు",
        "o1": "{service} దరఖాస్తు రుసుము రూ. {fee} గా నిర్ణయించడమైనది.",
        "o2": "ప్రతి దరఖాస్తును {days} పని దినాలలో పరిష్కరించాలి.",
        "o3": "నిర్ణీత గడువు దాటితే, ఆలస్యమైన ప్రతి రోజుకు రూ. {penalty} జరిమానా "
        "బాధ్యుడైన అధికారి నుండి వసూలు చేయబడుతుంది.",
        "o4": "రూ. {ceiling} వరకు విలువ గల కేసులను {officer} స్వయంగా ఆమోదించవచ్చు.",
        "o5": "నిర్ణయంతో అసంతృప్తి చెందిన దరఖాస్తుదారు {appeal_days} రోజులలోపు "
        "{appellate} వద్ద అప్పీలు దాఖలు చేయవచ్చు.",
        "o6": "ఈ ఉత్తర్వులు {effective} నుండి అమలులోకి వస్తాయి.",
        "table_heading": "జిల్లా వారీ మంజూరైన పోస్టులు మరియు కేటాయింపులు",
        "col_district": "జిల్లా",
        "col_target": "మంజూరైన పోస్టులు",
        "col_alloc": "కేటాయింపు (రూ. లక్షలలో)",
        "monitoring": "జిల్లా కలెక్టర్లు ప్రతి నెలా పురోగతిని సమీక్షించి నివేదికను "
        "శాఖాధిపతికి పంపాలి. ప్రతి దరఖాస్తు స్థితి ఆన్‌లైన్ పోర్టల్‌లో పౌరులకు "
        "కనిపించాలి; తిరస్కరణకు కారణాలను లిఖితపూర్వకంగా నమోదు చేయాలి.",
        "grievance": "ప్రతి కార్యాలయంలో ఫిర్యాదుల రిజిస్టర్ నిర్వహించాలి. ఫిర్యాదు "
        "అందిన రోజునే రసీదు ఇవ్వాలి, లిఖితపూర్వకంగా సమాధానం ఇవ్వాలి.",
        "supersedes": "ఈ ఉత్తర్వు గతంలో జారీ చేసిన {old_go_no} ను రద్దు చేస్తుంది.",
        "annex_heading": "అనుబంధం: {district} జిల్లా అమలు వివరాలు",
        "a1": "{district} జిల్లాలో ఇప్పటివరకు {a1} ప్రత్యేక శిబిరాలు నిర్వహించారు.",
        "a2": "జిల్లాలో మొత్తం {a2} దరఖాస్తులు అందాయి.",
        "a3": "వీటిలో {a3} దరఖాస్తులు పరిష్కరించబడ్డాయి.",
        "a4": "ఈ పనుల కోసం {a4} మంది అధికారులను నియమించారు.",
        "a5": "పెండింగ్ దరఖాస్తులన్నింటినీ {a5} లోగా పరిష్కరించాలి.",
        "a6": "జిల్లాకు ఇప్పటివరకు ₹{a6} లక్షల నిధులు విడుదల చేశారు.",
        "signoff": "గవర్నర్ ఆదేశానుసారం, ప్రభుత్వ ముఖ్య కార్యదర్శి (కల్పితం).",
    },
    "hi": {
        "govt": "राज्य सरकार (काल्पनिक) - {dept_name}",
        "title": "सरकारी आदेश संख्या {go_no}, दिनांक {go_date}",
        "subject": "विषय: {service} सेवाएँ - शुल्क, समय-सीमा और कार्यान्वयन दिशानिर्देश - "
        "आदेश जारी।",
        "read": "संदर्भ: {ref}",
        "read_none": "संदर्भ: विभागाध्यक्ष के प्रस्ताव, दिनांक {prev_date}।",
        "background": "{dept_name} द्वारा दी जाने वाली {service} सेवाओं को पारदर्शी ढंग से "
        "और निर्धारित समय-सीमा में नागरिकों तक पहुँचाना सरकार का लक्ष्य है। पिछले वर्ष "
        "मामलों की संख्या में भारी वृद्धि के कारण ज़िला स्तर पर लंबित मामले बढ़ गए। इसलिए "
        "शुल्क, समय-सीमा और अपील प्रक्रिया में संशोधन करते हुए निम्नलिखित आदेश जारी "
        "किए जाते हैं।",
        "order_heading": "आदेश",
        "o1": "{service} आवेदन का प्रसंस्करण शुल्क ₹{fee} निर्धारित किया जाता है।",
        "o2": "प्रत्येक मामले का निपटारा {days} कार्य दिवसों में किया जाना चाहिए।",
        "o3": "निर्धारित समय-सीमा पार होने पर, देरी के प्रत्येक दिन के लिए ज़िम्मेदार "
        "अधिकारी से ₹{penalty} जुर्माना वसूला जाएगा।",
        "o4": "₹{ceiling} तक के मामलों को {officer} स्वयं स्वीकृत कर सकते हैं।",
        "o5": "निर्णय से असंतुष्ट आवेदक {appeal_days} दिनों के भीतर {appellate} के समक्ष "
        "अपील दायर कर सकता है।",
        "o6": "ये आदेश {effective} से लागू होंगे।",
        "table_heading": "ज़िलेवार स्वीकृत पद और आवंटन",
        "col_district": "ज़िला",
        "col_target": "स्वीकृत पद",
        "col_alloc": "आवंटन (₹ लाख में)",
        "monitoring": "ज़िला कलेक्टर हर महीने प्रगति की समीक्षा करेंगे और विभागाध्यक्ष को "
        "रिपोर्ट भेजेंगे। ऑनलाइन पोर्टल पर हर मामले की स्थिति नागरिकों को दिखाई देनी "
        "चाहिए और अस्वीकृति के कारण लिखित रूप में दर्ज किए जाने चाहिए।",
        "grievance": "प्रत्येक कार्यालय में शिकायत रजिस्टर रखा जाएगा। शिकायत प्राप्त होने के "
        "दिन ही पावती दी जाएगी और लिखित उत्तर दिया जाएगा।",
        "supersedes": "यह आदेश पूर्व में जारी {old_go_no} को निरस्त करता है।",
        "annex_heading": "परिशिष्ट: {district} ज़िले का कार्यान्वयन विवरण",
        "a1": "{district} ज़िले में अब तक {a1} विशेष शिविर आयोजित किए गए।",
        "a2": "ज़िले में कुल {a2} मामले प्राप्त हुए।",
        "a3": "इनमें से {a3} मामलों का निपटारा किया गया।",
        "a4": "इस कार्य के लिए {a4} अधिकारियों को तैनात किया गया है।",
        "a5": "सभी लंबित मामलों का निपटारा {a5} तक किया जाना है।",
        "a6": "ज़िले को अब तक ₹{a6} लाख की राशि जारी की गई है।",
        "signoff": "राज्यपाल के आदेश से, प्रमुख सचिव (काल्पनिक)।",
    },
}

SOP_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "title": "{dept_name} - Standard Operating Procedure for {sop_focus}",
        "intro": "This SOP sets out the steps to be followed from the receipt of a "
        "{service} application to the final decision. It applies to every office of "
        "the department and is read with the Government Order on fees and timelines.",
        "steps_heading": "Steps",
        "s1": "Step 1 - Receipt: the application shall be entered on the portal within "
        "{h} hours of receipt and an acknowledgement issued.",
        "s2": "Step 2 - Verification: verification of documents shall be completed "
        "within {d2} days.",
        "s3": "Step 3 - Scrutiny: each file shall be scrutinised by a team of {n3} "
        "officers.",
        "s4": "Step 4 - Decision: the competent officer shall take a decision within "
        "{d4} days of the scrutiny report.",
        "s5": "Step 5 - Communication: the decision shall be communicated to the "
        "applicant by SMS and letter within {d5} days.",
        "s6": "Step 6 - Records: disposed files shall be preserved for {y6} years.",
        "closing": "Any deviation from this SOP shall be recorded in the file with "
        "reasons and reported in the monthly review.",
    },
    "te": {
        "title": "{dept_name} - {service} ప్రామాణిక నిర్వహణ విధానం (SOP)",
        "intro": "ఈ ప్రామాణిక నిర్వహణ విధానం {service} దరఖాస్తుల స్వీకరణ నుండి తుది "
        "నిర్ణయం వరకు అనుసరించాల్సిన దశలను వివరిస్తుంది. ఇది శాఖలోని ప్రతి కార్యాలయానికి "
        "వర్తిస్తుంది.",
        "steps_heading": "దశలు",
        "s1": "దశ 1 - స్వీకరణ: దరఖాస్తు అందిన {h} గంటలలోపు పోర్టల్‌లో నమోదు చేసి రసీదు " "ఇవ్వాలి.",
        "s2": "దశ 2 - పరిశీలన: పత్రాల పరిశీలన {d2} రోజులలోపు పూర్తి చేయాలి.",
        "s3": "దశ 3 - స్క్రూటినీ: ప్రతి ఫైలును {n3} మంది అధికారుల బృందం పరిశీలిస్తుంది.",
        "s4": "దశ 4 - నిర్ణయం: సమర్థ అధికారి స్క్రూటినీ నివేదిక అందిన {d4} రోజులలోపు " "నిర్ణయం తీసుకోవాలి.",
        "s5": "దశ 5 - సమాచారం: నిర్ణయాన్ని {d5} రోజులలోపు దరఖాస్తుదారునికి SMS మరియు లేఖ "
        "ద్వారా తెలియజేయాలి.",
        "s6": "దశ 6 - రికార్డులు: పరిష్కరించిన ఫైళ్లను {y6} సంవత్సరాల పాటు భద్రపరచాలి.",
        "closing": "ఈ విధానం నుండి ఏదైనా మినహాయింపు ఉంటే కారణాలతో ఫైలులో నమోదు చేసి "
        "నెలవారీ సమీక్షలో నివేదించాలి.",
        "annex_heading": "అనుబంధం: {district} జిల్లా నిర్వహణ గమనికలు",
        "x1": "జిల్లాలో {x1} హెల్ప్ డెస్క్‌లు పనిచేస్తున్నాయి.",
        "x2": "సిబ్బందికి ఇప్పటివరకు {x2} శిక్షణా సమావేశాలు నిర్వహించారు.",
        "x3": "ప్రతి నెల {x3}వ తేదీన జిల్లా స్థాయి సమీక్ష సమావేశం జరుగుతుంది.",
        "x4": "{x4} రోజులకు మించి పెండింగ్‌లో ఉన్న ఫైళ్లను జిల్లా అధికారికి నివేదించాలి.",
        "x5": "ప్రతి నెల {x5}% ఫైళ్లను యాదృచ్ఛికంగా ఆడిట్ చేయాలి.",
        "x6": "హెల్ప్‌లైన్ వద్ద {x6} మంది సిబ్బంది అందుబాటులో ఉంటారు.",
    },
    "hi": {
        "title": "{dept_name} - {service} मानक संचालन प्रक्रिया (SOP)",
        "intro": "यह मानक संचालन प्रक्रिया {service} मामलों की प्राप्ति से अंतिम निर्णय तक "
        "अपनाए जाने वाले चरणों का वर्णन करती है। यह विभाग के प्रत्येक कार्यालय पर लागू "
        "होती है।",
        "steps_heading": "चरण",
        "s1": "चरण 1 - प्राप्ति: मामला प्राप्त होने के {h} घंटों के भीतर पोर्टल पर दर्ज "
        "करके पावती दी जाए।",
        "s2": "चरण 2 - सत्यापन: दस्तावेज़ों का सत्यापन {d2} दिनों के भीतर पूरा किया जाए।",
        "s3": "चरण 3 - जाँच: प्रत्येक फ़ाइल की जाँच {n3} अधिकारियों की टीम करेगी।",
        "s4": "चरण 4 - निर्णय: सक्षम अधिकारी जाँच रिपोर्ट मिलने के {d4} दिनों के भीतर "
        "निर्णय लेंगे।",
        "s5": "चरण 5 - सूचना: निर्णय की सूचना {d5} दिनों के भीतर आवेदक को SMS और पत्र "
        "द्वारा दी जाए।",
        "s6": "चरण 6 - अभिलेख: निपटाई गई फ़ाइलें {y6} वर्षों तक सुरक्षित रखी जाएँ।",
        "closing": "इस प्रक्रिया से किसी भी विचलन को कारण सहित फ़ाइल में दर्ज किया जाए और "
        "मासिक समीक्षा में बताया जाए।",
        "annex_heading": "परिशिष्ट: {district} ज़िले के संचालन संबंधी नोट",
        "x1": "ज़िले में {x1} हेल्प डेस्क कार्यरत हैं।",
        "x2": "कर्मचारियों के लिए अब तक {x2} प्रशिक्षण सत्र आयोजित किए गए।",
        "x3": "हर महीने की {x3} तारीख को ज़िला स्तरीय समीक्षा बैठक होती है।",
        "x4": "{x4} दिनों से अधिक लंबित फ़ाइलों की सूचना ज़िला अधिकारी को दी जाए।",
        "x5": "हर महीने {x5}% फ़ाइलों का यादृच्छिक ऑडिट किया जाए।",
        "x6": "हेल्पलाइन पर {x6} कर्मचारी उपलब्ध रहते हैं।",
    },
}

# --- question templates -------------------------------------------------------

Q_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "row": "In the {title}, what is the {label} recorded for {id_label} {row_id}?",
        "target": "According to the district targets sheet of the {title}, what is the "
        "annual target for {district}?",
        "count": "How many {noun} records in the {title} are from {district} district?",
        "target_sum": "What is the total annual target across all districts in the "
        "district targets sheet of the {title}?",
        "csv_count": "How many entries in the {title} are from {district} district?",
        "rec_fee": "Under the latest government order of the {dept_name}, what is the "
        "processing fee for a {service} application?",
        "rec_days": "Under the current government order of the {dept_name}, within how "
        "many working days must a {service} application be disposed of?",
        "go_alloc": "As per Government Order {go_no}, what is the allocation for "
        "{district} district?",
        "sop_d2": "Under the {dept_name} SOP, within how many days must document "
        "verification be completed?",
        "sop_d4": "Under the {dept_name} SOP, within how many days of the scrutiny "
        "report must the competent officer decide?",
        "go_ceiling": "Under the latest government order of the {dept_name}, up to what "
        "value can the {officer} approve cases without further reference?",
        "go_penalty": "Under the latest government order of the {dept_name}, what penalty "
        "per day of delay is recovered from the officer responsible?",
        "sop_n3": "Under the {dept_name} SOP, how many officers scrutinise each file?",
        "sop_d5": "Under the {dept_name} SOP, within how many days must the decision be "
        "communicated to the applicant?",
        "join": "{q1} Also, {q2}",
    },
    "te": {
        "a1": "{dept} ప్రభుత్వ ఉత్తర్వు అనుబంధం ప్రకారం {district} జిల్లాలో ఎన్ని ప్రత్యేక "
        "శిబిరాలు నిర్వహించారు?",
        "a2": "{dept} ప్రభుత్వ ఉత్తర్వు ప్రకారం {district} జిల్లాలో మొత్తం ఎన్ని " "దరఖాస్తులు అందాయి?",
        "a3": "{district} జిల్లాలో {dept} కు అందిన దరఖాస్తులలో ఎన్ని పరిష్కరించబడ్డాయి?",
        "a4": "{dept} సేవల అమలు కోసం {district} జిల్లాలో ఎంత మంది అధికారులను నియమించారు?",
        "a5": "{district} జిల్లాలో {dept} పెండింగ్ దరఖాస్తులను ఏ తేదీలోగా పరిష్కరించాలి?",
        "a6": "{dept} ప్రభుత్వ ఉత్తర్వు ప్రకారం {district} జిల్లాకు ఎంత నిధులు విడుదల " "చేశారు?",
        "a6_recent": "తాజా ప్రభుత్వ ఉత్తర్వు ప్రకారం {dept} కింద {district} జిల్లాకు "
        "ప్రస్తుతం విడుదలైన నిధులు ఎంత?",
        "x1": "{dept} SOP ప్రకారం {district} జిల్లాలో ఎన్ని హెల్ప్ డెస్క్‌లు " "పనిచేస్తున్నాయి?",
        "x2": "{district} జిల్లాలో {dept} సిబ్బందికి ఎన్ని శిక్షణా సమావేశాలు నిర్వహించారు?",
        "x3": "{dept} SOP ప్రకారం {district} జిల్లా సమీక్ష సమావేశం ప్రతి నెల ఏ తేదీన " "జరుగుతుంది?",
        "x4": "{dept} SOP ప్రకారం {district} జిల్లాలో ఎన్ని రోజులకు మించి పెండింగ్‌లో "
        "ఉన్న ఫైళ్లను జిల్లా అధికారికి నివేదించాలి?",
        "x5": "{dept} SOP ప్రకారం {district} జిల్లాలో ప్రతి నెల ఎంత శాతం ఫైళ్లను ఆడిట్ " "చేయాలి?",
        "x6": "{district} జిల్లాలో {dept} హెల్ప్‌లైన్ వద్ద ఎంత మంది సిబ్బంది అందుబాటులో " "ఉంటారు?",
        "row": "{title} ప్రకారం {row_id} యొక్క {label} ఎంత?",
        "go_penalty": "తాజా {dept_name} ప్రభుత్వ ఉత్తర్వు ప్రకారం గడువు దాటితే ఆలస్యమైన "
        "ప్రతి రోజుకు ఎంత జరిమానా విధిస్తారు?",
        "join": "{q1} అలాగే, {q2}",
    },
    "hi": {
        "a1": "{dept} के सरकारी आदेश के परिशिष्ट के अनुसार {district} ज़िले में कितने "
        "विशेष शिविर आयोजित किए गए?",
        "a2": "{dept} के सरकारी आदेश के अनुसार {district} ज़िले में कुल कितने मामले प्राप्त " "हुए?",
        "a3": "{district} ज़िले में {dept} को प्राप्त मामलों में से कितनों का निपटारा हुआ?",
        "a4": "{district} ज़िले में {dept} के कार्य के लिए कितने अधिकारी तैनात किए गए हैं?",
        "a5": "{district} ज़िले में {dept} के लंबित मामलों का निपटारा किस तारीख तक करना है?",
        "a6": "{dept} के सरकारी आदेश के अनुसार {district} ज़िले को कितनी राशि जारी की गई है?",
        "a6_recent": "नवीनतम सरकारी आदेश के अनुसार {dept} के तहत {district} ज़िले को अब तक "
        "कितनी राशि जारी की गई है?",
        "x1": "{dept} SOP के अनुसार {district} ज़िले में कितने हेल्प डेस्क कार्यरत हैं?",
        "x2": "{district} ज़िले में {dept} कर्मचारियों के लिए कितने प्रशिक्षण सत्र आयोजित "
        "किए गए?",
        "x3": "{dept} SOP के अनुसार {district} ज़िले की समीक्षा बैठक हर महीने किस तारीख को "
        "होती है?",
        "x4": "{dept} SOP के अनुसार {district} ज़िले में कितने दिनों से अधिक लंबित फ़ाइलों "
        "की सूचना ज़िला अधिकारी को दी जानी चाहिए?",
        "x5": "{dept} SOP के अनुसार {district} ज़िले में हर महीने कितने प्रतिशत फ़ाइलों का "
        "ऑडिट किया जाना चाहिए?",
        "x6": "{district} ज़िले में {dept} हेल्पलाइन पर कितने कर्मचारी उपलब्ध रहते हैं?",
        "row": "{title} के अनुसार {row_id} का {label} क्या है?",
        "join": "{q1} साथ ही, {q2}",
    },
}

ANNEX_FACTS_EN = {
    "a1": "{district} district held {v} special camps",
    "a2": "{district} district received {v} applications in total",
    "a3": "{v} applications were disposed of in {district} district",
    "a4": "{v} officers were deployed in {district} district",
    "a5": "pending applications in {district} district must be disposed of by {v}",
    "a6": "Rs {v} lakh has been released to {district} district",
    "x1": "{district} district has {v} help desks",
    "x2": "{v} training sessions were held for staff in {district} district",
    "x3": "the district review meeting is held on day {v} of every month",
    "x4": "files pending more than {v} days are reported to the district officer",
    "x5": "{v}% of files are audited at random every month",
    "x6": "{v} staff are available at the helpline",
}
