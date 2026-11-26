class ErrorCodes:
    COMPUTATION_ERROR = 1001
    INPUT_VALIDATION_ERROR = 1002
    NO_SOLUTION = 1003


class BalancerError(Exception):
    def __init__(self, error_code: int, message: str) -> None:
        super().__init__()
        self.error_code = error_code
        self.message = message
