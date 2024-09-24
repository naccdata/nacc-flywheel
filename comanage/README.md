# COManage Core API

COManage is the CILogon user registry, and the CoreAPI is used to manage COPerson objects representing users.

## Generating Client Files

The file `comanage/coreapi.yaml' is used to generate the Python SDK for using the Core API.
This file can be updated with the command

```bash
curl -OL --output-dir comanage https://raw.githubusercontent.com/Internet2/comanage-registry/develop/app/Plugin/CoreApi/Config/Schema/coreapi.yaml
```

at the top-level of the repository.
Then the files generated with the command 

```bash
pants run comanage:build_client
```

Note that generated files aren't included in the repository.
The file `comanage/coreapi/src/python/BUILD` is part of the repository, and prevents Pants from wanting to add BUILD files

Once generated, the documentation can be found in [comanage/coreapi/src/python/coreapi_client_README.md](comanage/coreapi/src/python/coreapi_client_README.md)

## References

[COManage Core API](https://spaces.at.internet2.edu/display/COmanage/Core+API)

[Core API message schema](https://github.com/Internet2/comanage-registry/blob/develop/app/Plugin/CoreApi/Config/Schema/message.json)

[Core API openapi](https://github.com/Internet2/comanage-registry/blob/develop/app/Plugin/CoreApi/Config/Schema/coreapi.yaml)