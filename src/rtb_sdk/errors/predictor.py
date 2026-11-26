from typing import Literal


type ErrorCodesType = Literal[0, 1, 2]

class ErrorCodes:
    UNKNOWN_ERROR_CODE: ErrorCodesType = 0
    VALIDATION_ERROR_CODE: ErrorCodesType = 1
    PARAMETER_ERROR_CODE: ErrorCodesType = 2

class PredictorError(Exception):
    def __init__(self, error_code: ErrorCodesType, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(self.error_code, self.message)
