import sys

try:
    from controller.transfer import handlers
    import model
    import util
    import tests
    import exceptions
except:
    # drone puts everything in a src folder
    from src import model, tests, util, exceptions

sys.modules["model"] = model
sys.modules["tests"] = tests
sys.modules["util"] = util
sys.modules["exceptions"] = exceptions
