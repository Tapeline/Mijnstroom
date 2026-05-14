# Backend architecture notice

Backend should be structured as follows:

- app package (mijnstroom)
    - common (common utilities relying solely on the language and not
	   connected to any layer in any way)
	- domain (domain models, invariants)
	- application (interactors and interfaces they use)
	- infrastructure (interfaces implementations)
	- presentation (actual routes calling interactors, app exception mapping to error codes)
	- bootstrap (entrypoints: main and worker, configuration of logging,
	  yml config loading)
	  
Examples:

Domain model

```
MyEntityId = NewType("MyEntityId", str)
@entity
class MyEnitiy:
    id: MyEntityId
	author: UserId
	name: str
	
	def __post_init__(self):
		if not name: raise InvalidName("Cannot be blank")
```

Interactor

```
@interactor
class CreateMyEntity:
    repo: MyEntityRepo
    tx: Transaction
    idp: UserIdProvider

async def __call__(self, dto: CreateEntityDTO) -> MyEntity:
	async with self.tx:
		user = await self.idp.require_user()
		entity = MyEntity(generate_id(MyEntityId), user.id, dto.name)
		await self.repo.insert(entity)
		return entity
```

Repo interface

```
class MyEntityRepo(Protocol):
    @abstractmethod
    async def insert(entity: MyEntity) -> None: ...
```

Error mapping

```
def error_handler...(err, ...): # some litestar error handler def
    ...
    status_code, error_code = map_error(err)
	...

def map_error(err):
	match err:
		InvalidName():
			return 400, "invalid_name"
```

`@entity` and such decorators are just `@dataclass_transform`'s (residing in commons module)

For DI use dishka
