class ProposalError(Exception):
    def __init__(self, *args, **kwargs):
        # Call the base class constructor with the parameters it needs
        super().__init__(*args, **kwargs)

class EmptyProposalError(Exception):
    def __init__(self, *args, **kwargs):
        # Call the base class constructor with the parameters it needs
        super().__init__(*args, **kwargs)
