"""Entry script for Refresh REDCap Download URLs."""

import logging
import os
import boto3

from typing import Optional
from dotenv import load_dotenv

from flywheel_gear_toolkit import GearToolkitContext
from gear_execution.gear_execution import (ClientWrapper, ContextClient,
                                           GearEngine,
                                           GearExecutionEnvironment)
from redcap_refresh_dl_urls_app.main import run
from inputs.parameter_store import ParameterStore
from redcap.redcap_connection import REDCapConnection

log = logging.getLogger(__name__)

class REDCapRefreshDownloadURLs(GearExecutionEnvironment):
    """Visitor for the templating gear."""

    def __init__(self, client: ClientWrapper):
        super().__init__(client=client)

    @classmethod
    def create(
        cls,
        context: GearToolkitContext,
        parameter_store: Optional[ParameterStore] = None
    ) -> 'REDCapRefreshDownloadURLs':
        """Creates a gear execution object.

        Args:
            context: The gear context.
            parameter_store: The parameter store
        Returns:
          the execution environment
        Raises:
          GearExecutionError if any expected inputs are missing
        """
        client = ContextClient.create(context=context)

        return REDCapRefreshDownloadURLs(client=client)

    def run(self, context: GearToolkitContext) -> None:

        ssm = boto3.client('ssm')
        parameter = ssm.get_parameter(Name='/redcap/aws/pid_83/token', WithDecryption=True)
        token = parameter['Parameter']['Value']
        url = 'https://redcap.naccdata.org/api/'
        #print(f'token: {token}')

        redcap_con = REDCapConnection(token=token, url=url)
        
        run(proxy=self.proxy, redcap_con=redcap_con)
        
def main():
    """Main method for Refresh REDCap Download URLs."""

    context = GearToolkitContext()

    env_file_path = context.get_input_path('dotenv')
        
    if env_file_path is not None:
        print('loading environment variables from file')
        load_dotenv(env_file_path, override=True)

    #print(os.environ)

    GearEngine.create_with_parameter_store().run(gear_type=REDCapRefreshDownloadURLs)

if __name__ == "__main__":
    main()
