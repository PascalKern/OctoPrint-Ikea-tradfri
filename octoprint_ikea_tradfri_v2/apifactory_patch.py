


# Try to patch the APIFactory for issue with try to regenerate a psk with existing identity
# old__get_response = APIFactory._get_response
# async def new__get_response(self, msg):
#     # Here should modify to pr_resp = await pr_req.response_raising instead of response!
#     self._logger.debug("------- It Worked!")
#     return await old__get_response(self, msg)
# APIFactory._get_response = new__get_response

# # Second try - might work...
# import ast
# import inspect
# # from pytradfri.api.aiocoap_api import APIFactory as OldAPIFactory
# # source = inspect.getsource(APIFactory)
# source = inspect.getsource(APIFactory._get_response)
# # source = inspect.getsource(APIFactory._get_response)
# # self._logger.debug("Source: ", source)
# src = source.split('\n')
# # self._logger.debug("Src: ", src)
# indent = len(src[0]) - len(src[0].lstrip())
# # self._logger.debug("Indent: ", indent)
# s = '\n'.join(i[indent:] for i in src)
# # self._logger.debug("S: ", s)
# tree = ast.parse(s)
# # tree = ast.parse(source=source)
# # self._logger.debug("Tree: ", tree)
# n_s = ast.parse("pr_resp = await pr_req.response_raising")
# # tree.body[0].body[8].body[1].body[2] = n_s.body[0]  # In whole class
# tree.body[0].body[1].body[2] = n_s.body[0]  # Only _get_response
# exec(compile(tree, 'aiocoap_api_edit.py', 'exec'))
# # exec(compile(tree, '<string>', 'exec'))
# APIFactory._get_response = _get_response  # The right hand part is the function generated in global namespace by exec(compile(
# del _get_response
# # APIFactory = APIFactory
# # APIFactory = OldAPIFactory
# # del OldAPIFactory
#
# # from pytradfri.api.aiocoap_api import APIFactory
