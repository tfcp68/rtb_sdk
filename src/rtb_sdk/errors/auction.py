class ErrorCodes:
    AUCTION_MATH_ERROR_CODE=1
    WRONG_DATA_FORMAT_ERROR_CODE=2


class AuctionError(Exception):
    def __init__(self, error_code: int, message: str) -> None:
        super().__init__()
        self.error_code = error_code
        self.message = message