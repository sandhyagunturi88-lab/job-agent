"""DWP Find a Job (findajob.dwp.gov.uk).

There is no official public API for Find a Job; automated access requires
either the employer/partner interface or explicit permission. This source
stays mocked until that decision is made with the user — do NOT scrape it.
"""

from jobpilot_schemas import Job

from worker.sources._mock import mock_jobs


class DWPFindAJobSource:
    name = "dwp_find_a_job"

    async def fetch(self) -> list[Job]:
        return mock_jobs("dwp_find_a_job")
