class EnvironmentVariableNotFound(Exception):
    def __init__(self, env_var_name: str):
        self.message = f"[ASE:000] Environment variable ${env_var_name} not found"
        super().__init__(self.message)


class PersistenceObjectDoesNotExist(Exception):
    def __init__(self, e: str):
        self.message = f"[ASE:001] Object does not exist: {e}"
        super().__init__(self.message)


class UnableToFetchTaskLookupFromPersistence(Exception):
    def __init__(self, e: str):
        self.message = (
            f"[ASE:002] Unable to fetch market insights from persistence: {e}"
        )
        super().__init__(self.message)


class SessionNotFoundForUser(Exception):
    def __init__(self, e: str):
        self.message = f"[ASE:003] Unable to find session for user: {e}"
        super().__init__(self.message)


class MissingUserIdError(Exception):
    def __init__(self):
        self.message = "[ASE:004] user_id is required but not provided in request metadata. Either authenticate or interact in dev mode"
        super().__init__(self.message)


class AuthorisationTokenMissing(Exception):
    def __init__(self):
        self.message = "[ASE:005] Authorization token in header is missing"
        super().__init__(self.message)


class UnableToAuthenticateToken(Exception):
    def __init__(self, message: str):
        self.message = f"[ASE:006] {message}"
        super().__init__(self.message)


class InvalidWhereConditions(Exception):
    def __init__(self, conditions: str):
        self.message = f"[ASE:007] Invalid SQL WHERE conditions: {conditions}"
        super().__init__(self.message)


class FailureDuringCompaction(Exception):
    def __init__(self, message: str):
        self.message = f"[ASE:008] Oops! {message}"
        super().__init__(self.message)


class UnauthorisedRequest(Exception):
    def __init__(self, message: str):
        self.message = f"[ASE:009] Unauthorised Request. {message}"
        super().__init__(self.message)
