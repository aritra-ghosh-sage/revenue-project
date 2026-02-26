import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import ClassVar, Optional


logger = logging.getLogger(__name__)


@dataclass
class SKU:
    sforce_link: str
    sku_name: str
    contract: bool
    contract_link: Optional[str]
    company_id: str
    intacct_cid: str
    parent: str
    flag: bool
    last_gl_txn_date: date
    link: str
    total_gl_txn: int


@dataclass
class UsageData:
    contract_id: str
    order_id: str
    account_name: str
    account_owner: str
    channel: str
    partner: Optional[str]
    period: str  # e.g. "January 2026"

    api_usage: int = 0
    api_over: int = 0
    api_est_dollars: Decimal = Decimal("0")

    apa_usage: int = 0
    apa_over: int = 0
    apa_est_dollars: Decimal = Decimal("0")

    das_usage: int = 0
    das_over: int = 0

    # optional if you still want explicit SKU naming
    sku_name: Optional[str] = None

    # class variable for mock data
    _mock_rows: ClassVar[list["UsageData"]] = []

    # ---- compatibility with your SKU class fields ----
    @property
    def sforce_name(self) -> str:
        return self.account_name

    @property
    def contract(self) -> str:
        return self.contract_id

    @property
    def company_id(self) -> str:
        return self.order_id

    @property
    def parent(self) -> Optional[str]:
        return self.partner

    @classmethod
    def _clean_string(cls, value: object) -> Optional[str]:
        if value is None:
            logger.debug("UsageData filter rejected missing string input")
            return None
        text = str(value).strip()
        if not text:
            logger.debug("UsageData filter rejected empty string input")
            return None
        return text.lower()

    @classmethod
    def _clean_decimal(cls, value: object) -> Optional[Decimal]:
        if value is None or isinstance(value, bool):
            logger.debug("UsageData filter rejected non-numeric input")
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            logger.debug("UsageData filter rejected invalid numeric input: %r", value)
            return None

    @classmethod
    def _filter_by_string(
        cls, field_name: str, value: object, partial: bool = False
    ) -> list["UsageData"]:
        needle = cls._clean_string(value)
        if needle is None:
            return []

        matches: list["UsageData"] = []
        for row in cls._mock_rows:
            hay = getattr(row, field_name, None)
            if hay is None:
                continue
            hay_text = str(hay).lower()
            if partial:
                if needle in hay_text:
                    matches.append(row)
            else:
                if needle == hay_text:
                    matches.append(row)
        return matches

    @classmethod
    def _filter_by_number(cls, field_name: str, value: object) -> list["UsageData"]:
        """Filter by numeric field value using greater than or equal to comparison.
        
        Handles both int and Decimal field types properly.
        For int fields, compares as integers.
        For Decimal fields, compares as Decimals.
        Returns all rows where field value >= input value.
        """
        if value is None or isinstance(value, bool):
            logger.debug("UsageData filter rejected non-numeric input")
            return []
        
        # Try to determine if we're dealing with an integer or decimal field
        # by checking the first row's field type
        matches: list["UsageData"] = []
        
        if not cls._mock_rows:
            return matches
        
        # Get the field type from the first row
        sample_value = getattr(cls._mock_rows[0], field_name)
        is_int_field = isinstance(sample_value, int)
        
        if is_int_field:
            # For integer fields, convert and compare as int
            try:
                target_int = int(str(value).strip())
            except (ValueError, AttributeError):
                logger.debug("UsageData filter rejected invalid integer input: %r", value)
                return []
            
            for row in cls._mock_rows:
                try:
                    candidate = int(getattr(row, field_name))
                    if candidate >= target_int:
                        matches.append(row)
                except (ValueError, AttributeError):
                    continue
        else:
            # For Decimal fields, convert and compare as Decimal
            try:
                target_decimal = Decimal(str(value).strip())
            except (InvalidOperation, ValueError, AttributeError):
                logger.debug("UsageData filter rejected invalid decimal input: %r", value)
                return []
            
            for row in cls._mock_rows:
                try:
                    candidate = Decimal(str(getattr(row, field_name)))
                    if candidate >= target_decimal:
                        matches.append(row)
                except (InvalidOperation, ValueError, AttributeError):
                    continue
        
        return matches

    @classmethod
    def _filter_by_total_usage(cls, value: object) -> list["UsageData"]:
        """Filter by total usage (>= comparison)."""
        target = cls._clean_decimal(value)
        if target is None:
            return []

        matches: list["UsageData"] = []
        for row in cls._mock_rows:
            total = Decimal(row.api_usage + row.apa_usage + row.das_usage)
            if total >= target:
                matches.append(row)
        return matches

    @classmethod
    def _filter_by_total_over(cls, value: object) -> list["UsageData"]:
        """Filter by total overage usage (>= comparison)."""
        target = cls._clean_decimal(value)
        if target is None:
            return []

        matches: list["UsageData"] = []
        for row in cls._mock_rows:
            total = Decimal(row.api_over + row.apa_over + row.das_over)
            if total >= target:
                matches.append(row)
        return matches

    @classmethod
    def _filter_by_total_est_dollars(cls, value: object) -> list["UsageData"]:
        """Filter by total estimated dollars (>= comparison)."""
        target = cls._clean_decimal(value)
        if target is None:
            return []

        matches: list["UsageData"] = []
        for row in cls._mock_rows:
            total = row.api_est_dollars + row.apa_est_dollars
            if total >= target:
                matches.append(row)
        return matches

    @classmethod
    def get_billing_by_period(cls, bill_period: str) -> list["UsageData"]:
        return cls._filter_by_string("period", bill_period)

    @classmethod
    def get_billing_by_contract_id(cls, contract_id: str) -> list["UsageData"]:
        return cls._filter_by_string("contract_id", contract_id)

    @classmethod
    def get_billing_by_order_id(cls, order_id: str) -> list["UsageData"]:
        return cls._filter_by_string("order_id", order_id)

    @classmethod
    def get_billing_by_account_name(cls, account_name: str) -> list["UsageData"]:
        return cls._filter_by_string("account_name", account_name, partial=True)

    @classmethod
    def get_billing_by_account_owner(cls, account_owner: str) -> list["UsageData"]:
        return cls._filter_by_string("account_owner", account_owner, partial=True)

    @classmethod
    def get_billing_by_channel(cls, channel: str) -> list["UsageData"]:
        return cls._filter_by_string("channel", channel, partial=True)

    @classmethod
    def get_billing_by_partner(cls, partner: str) -> list["UsageData"]:
        return cls._filter_by_string("partner", partner, partial=True)

    @classmethod
    def get_billing_by_usage(cls, usage: object) -> list["UsageData"]:
        return cls._filter_by_total_usage(usage)

    @classmethod
    def get_billing_by_over_usage(cls, over_usage: object) -> list["UsageData"]:
        return cls._filter_by_total_over(over_usage)

    @classmethod
    def get_billing_by_estimated_dollars(
        cls, estimated_dollars: object
    ) -> list["UsageData"]:
        return cls._filter_by_total_est_dollars(estimated_dollars)

    @classmethod
    def get_billing_by_api_usage(cls, api_usage: object) -> list["UsageData"]:
        return cls._filter_by_number("api_usage", api_usage)

    @classmethod
    def get_billing_by_api_over(cls, api_over: object) -> list["UsageData"]:
        return cls._filter_by_number("api_over", api_over)

    @classmethod
    def get_billing_by_api_est_dollars(
        cls, api_est_dollars: object
    ) -> list["UsageData"]:
        return cls._filter_by_number("api_est_dollars", api_est_dollars)

    @classmethod
    def get_billing_by_apa_usage(cls, apa_usage: object) -> list["UsageData"]:
        return cls._filter_by_number("apa_usage", apa_usage)

    @classmethod
    def get_billing_by_apa_over(cls, apa_over: object) -> list["UsageData"]:
        return cls._filter_by_number("apa_over", apa_over)

    @classmethod
    def get_billing_by_apa_est_dollars(
        cls, apa_est_dollars: object
    ) -> list["UsageData"]:
        return cls._filter_by_number("apa_est_dollars", apa_est_dollars)

    @classmethod
    def get_billing_by_das_usage(cls, das_usage: object) -> list["UsageData"]:
        return cls._filter_by_number("das_usage", das_usage)

    @classmethod
    def get_billing_by_das_over(cls, das_over: object) -> list["UsageData"]:
        return cls._filter_by_number("das_over", das_over)


UsageData._mock_rows = [
    UsageData(
        "C18995",
        "C1922",
        "Curis Services",
        "Julio Rios",
        "VAR",
        "Intellitec Solutions",
        "January 2026",
        48876,
        0,
        Decimal("0"),
        7462,
        7462,
        Decimal("3731"),
        3927566,
        392756,
    ),
    UsageData(
        "C19406",
        "C19406",
        "Sun Meridian Management",
        "Dave Gallo",
        "Direct",
        None,
        "January 2026",
        55144,
        0,
        Decimal("0"),
        5740,
        3740,
        Decimal("1870"),
        1122770,
        112276,
    ),
    UsageData(
        "C20506",
        "C20506",
        "FusionSite Services, LLC",
        "Monica Lopez",
        "Direct",
        None,
        "January 2026",
        224796,
        124796,
        Decimal("2121"),
        4140,
        2140,
        Decimal("1070"),
        0,
        0,
    ),
    UsageData(
        "C21926",
        "C21926",
        "Tide Health Group LLC",
        "Mike Turner",
        "Direct",
        None,
        "January 2026",
        769,
        0,
        Decimal("0"),
        2201,
        1951,
        Decimal("976"),
        0,
        0,
    ),
    UsageData(
        "C22209",
        "C1529",
        "McCarthy Management Group",
        "Tiffany Sullivan",
        "VAR",
        "Baker Tilly Advisory Group",
        "January 2026",
        0,
        0,
        Decimal("0"),
        5900,
        1900,
        Decimal("950"),
        0,
        0,
    ),
    UsageData(
        "C6337",
        "C6337",
        "Signature Dental Partners",
        "Jeff Onesto",
        "Direct",
        None,
        "January 2026",
        5314,
        0,
        Decimal("0"),
        2783,
        1783,
        Decimal("892"),
        0,
        0,
    ),
    UsageData(
        "C24645",
        "C24645",
        "Bellair",
        "Tyler Nollette",
        "Direct",
        None,
        "January 2026",
        6095,
        0,
        Decimal("0"),
        2132,
        1632,
        Decimal("816"),
        0,
        0,
    ),
    UsageData(
        "C4019",
        "C4019",
        "Generations Healthcare",
        "Nicole Dawson",
        "Direct",
        None,
        "January 2026",
        0,
        0,
        Decimal("0"),
        1758,
        1508,
        Decimal("754"),
        9875,
        0,
    ),
    UsageData(
        "C21234",
        "C21234",
        "CCHS",
        "Mark Montenero",
        "Direct",
        None,
        "January 2026",
        16566,
        0,
        Decimal("0"),
        1457,
        1457,
        Decimal("729"),
        0,
        0,
    ),
    UsageData(
        "C7414",
        "C1529",
        "Essential Services Holdings",
        "Tiffany Sullivan",
        "VAR",
        "Baker Tilly Advisory Group",
        "January 2026",
        721590,
        0,
        Decimal("0"),
        1444,
        1444,
        Decimal("722"),
        5432,
        0,
    ),
]


@dataclass
class AllocationUsage:
    sfdc_link: bool
    cny: str
    company_id: str
    intacct_cid: str
    parent: str
    link: str
    intacct: bool
    contract: bool
    flag: bool
    contract_link: bool
    subscribed: date
    allocations: int
    last_gl: date
    last_run: date

    _mock_rows: ClassVar[list["AllocationUsage"]] = []

    @classmethod
    def get_allocation_sku_records(cls) -> list["AllocationUsage"]:
        """Filter allocation SKU records matching:
        - contract = False
        - flag = True
        - allocations > 0
        - last_run within last 12 months (rolling)
        """
        from datetime import datetime, timedelta
        
        # Calculate 12 months ago from today
        twelve_months_ago = datetime.now().date() - timedelta(days=365)
        
        matches: list["AllocationUsage"] = []
        for row in cls._mock_rows:
            if (
                not row.contract 
                and row.flag 
                and row.allocations > 0
                and row.last_run >= twelve_months_ago
            ):
                matches.append(row)
        
        return matches


AllocationUsage._mock_rows = [
    AllocationUsage(
        True,
        "224613",
        "ESP ESPA",
        "C17635",
        "GRF CPAs",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2022, 2, 2),
        101402,
        date(2026, 2, 1),
        date(2023, 1, 17),
    ),
    AllocationUsage(
        True,
        "50401000277097",
        "soa",
        "C23311",
        "larsonallenvar",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2025, 6, 2),
        52,
        date(2026, 2, 1),
        date(2025, 9, 16),
    ),
    AllocationUsage(
        True,
        "101000000000541",
        "CITCI",
        "C9194",
        "accttwo",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2020, 8, 27),
        22111,
        date(2026, 2, 1),
        date(2026, 2, 10),
    ),
    AllocationUsage(
        True,
        "185172",
        "BronxWorks",
        "C7398",
        "larsonallenvar",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2023, 10, 9),
        292,
        date(2026, 1, 1),
        date(2023, 12, 4),
    ),
    AllocationUsage(
        True,
        "10701000279125",
        "loapproperties",
        "C26861",
        "larsonallenvar",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2022, 12, 29),
        6661,
        date(2025, 11, 1),
        date(2025, 11, 2),
    ),
    AllocationUsage(
        True,
        "1010000000030835",
        "catalystmedicalgroup",
        "C15767",
        "larsonallenvar",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2022, 12, 29),
        8909,
        date(2025, 11, 1),
        date(2025, 9, 20),
    ),
    AllocationUsage(
        True,
        "189722",
        "Hollywood Feed",
        "C7843",
        "Hollywood Feed",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2019, 7, 19),
        25,
        date(2025, 9, 1),
        date(2025, 9, 11),
    ),
    AllocationUsage(
        True,
        "101000000003000",
        "essentialaccess",
        "C9802",
        "armaninovar",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2026, 2, 4),
        229,
        date(2025, 8, 1),
        date(2025, 8, 25),
    ),
    AllocationUsage(
        True,
        "160239",
        "TPLV",
        "C4571",
        "Acumen",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2021, 2, 14),
        12651,
        date(2025, 7, 1),
        date(2025, 7, 23),
    ),
    AllocationUsage(
        True,
        "205138",
        "Rubicon Programs",
        "C9110",
        "Rubicon Programs",
        "BILLABLE - SINGLE CNY",
        True,
        False,
        True,
        True,
        date(2020, 7, 29),
        28717,
        date(2025, 7, 1),
        date(2025, 7, 24),
    ),
]
