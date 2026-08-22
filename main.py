from dify_plugin import DifyPluginEnv, Plugin

# Video renders can take several minutes; allow long-running tool invocations.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=900))

if __name__ == "__main__":
    plugin.run()
