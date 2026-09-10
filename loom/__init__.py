import socket
import os




running_at_enbw = False




host_name = socket.gethostname()
if "ENBW-" in host_name:
    running_at_enbw = True




# AOP (DEV)
os.environ['AOP_DEV_CLIENT_ID'] = '7vd3agu73aqlj7shg4cir2k042'
os.environ['AOP_DEV_CLIENT_SECRET'] = 'u9tlu6mu3cor1nb7s2nd2fdn2nlvo4pk6ja2fp9t1o8cl16cvfg'
os.environ['AOP_DEV_API_KEY'] = 'RWiNr6ZlZJ4mwMEt5nbcj3A3nsUFPtTU5FgC1vPE'

# AOP (PROD)
os.environ['AOP_PROD_CLIENT_ID'] = '1bthhqu36unovk2nnh0f4cuq91'
os.environ['AOP_PROD_CLIENT_SECRET'] = '1p08jd65r7tf8n1v2710147amienb3bu3inceg29bj204mm948ie'
os.environ['AOP_PROD_API_KEY'] = 'YdxtLAM8WwaddbIxeIUuEaNCOvMwf65M7seBuutp'

# AOP (TEST)
os.environ['AOP_TEST_CLIENT_ID'] = '1bbvvme49sa5f0a2omaa8f53uo'
os.environ['AOP_TEST_CLIENT_SECRET'] = '1min1l1t6fb9dpkvhhnmf3jog6tpmj880qu6gq0vi5g3le3g3l62'
os.environ['AOP_TEST_API_KEY'] = 'IjqoZGCkSg3mkRWAyy10h92otgV3urv56JRVTJOB'

# DBB MDD (PROD)
os.environ['DBBMDD_PROD_ACCESS_URL'] = 'https://api.conapi-prod.enbw.cloud'
os.environ['DBBMDD_PROD_ACCESS_USER'] = 'imp-pfcsml-prod'
os.environ['DBBMDD_PROD_ACCESS_SECRET'] = '=i*U2?jB*?;H8q.gXkeq'
os.environ['DBBMDD_PROD_CLIENT_ID'] = '1ic65fvc7dj9uflgav042be42a'
os.environ['DBBMDD_PROD_POOL_ID'] = 'eu-central-1_Rqum9OMQi'
os.environ['DBBMDD_PROD_POOL_REGION'] = 'eu-central-1'

# DBB (PROD)
os.environ['DBB_PROD_ACCESS_URL'] = 'https://api.conapi-prod.enbw.cloud'
os.environ['DBB_PROD_ACCESS_USER'] = 'imp-pfcsml-prod'
os.environ['DBB_PROD_ACCESS_SECRET'] = '=i*U2?jB*?;H8q.gXkeq'
os.environ['DBB_PROD_CLIENT_ID'] = '1ic65fvc7dj9uflgav042be42a'
os.environ['DBB_PROD_POOL_ID'] = 'eu-central-1_Rqum9OMQi'
os.environ['DBB_PROD_POOL_REGION'] = 'eu-central-1'

# DBB (PREPROD)
os.environ['DBB_PREPROD_ACCESS_URL'] = 'https://api.conapi-preprod.enbw.cloud'
os.environ['DBB_PREPROD_ACCESS_USER'] = 'imp-marketsimulation-preprod'
os.environ['DBB_PREPROD_ACCESS_SECRET'] = 'v8RJT:xGImq!98kPw=sL'
os.environ['DBB_PREPROD_CLIENT_ID'] = '6e2jgea3rb64mjuf86hd821esi'
os.environ['DBB_PREPROD_POOL_ID'] = 'eu-central-1_0VjN2IzU1'
os.environ['DBB_PREPROD_POOL_REGION'] = 'eu-central-1'

# tradingcurveengine (TEST)
os.environ['TCE_TEST_SERVICE_URL'] = "https://hku2l7uz40.execute-api.eu-central-1.amazonaws.com/orderbook"
os.environ['TCE_TEST_TOKEN_URL'] = 'https://enbw-tradingcurveengine-test.auth.eu-central-1.amazoncognito.com/oauth2/token'
os.environ['TCE_TEST_SCOPE'] = 'api.tradingcurveng-test.enbw.cloud/API_ACCESS'
os.environ['TCE_TEST_CLIENT_ID'] = '14tmlrhl8krqqgvr00584s4vq3'
os.environ['TCE_TEST_SECRET_ID'] = '8cclqkeuu1kjm9e30db0igs93jnbpos7jabah9q76irunddclvn'

# tradingcurveengine (PROD)
os.environ['TCE_PROD_SERVICE_URL'] = "https://api.enbw-power-pfc.tradingcurveeng-prod.enbw.cloud/orderbook"
os.environ['TCE_PROD_TOKEN_URL'] = "https://enbw-tradingcurveengine-enbw-power-pfc-prod.auth.eu-central-1.amazoncognito.com/oauth2/token"
os.environ['TCE_PROD_SCOPE'] = f"api.tradingcurveng-prod.enbw.cloud/API_ACCESS"
os.environ['TCE_PROD_CLIENT_ID'] = "39puls9ok1pm0tpokn9g4qdm85"
os.environ['TCE_PROD_SECRET_ID'] = "2d4b4vfjjjudlvaou12td58b0cg4ihfnqejj6hh49oul9qi6lhl"

# Volue (External Data Vendor)
os.environ['VOLUE_CLIENT_ID'] = 'kItE4JM-eUWhW4NQ481luwVfHP-LTlHl'
os.environ['VOLUE_ACCESS_USER'] = '4gJtNdHRYqvss2B-SssRq2zIFbxE5R.HEmApNwZFQEB0NUJrKfONRotWCMf1KSXghBebWI6K5mCpUHSd.lPUS-Zm3mYf7ZNhT4V7'

# Vendohm (External Data Vendor)
os.environ['VENDOHM_DB_URL'] = '35.234.91.142:5432/warehouse'
os.environ['VENDOHM_DB_USER'] = 'lchrist'
os.environ['VENDOHM_DB_SECRET'] = 'GoLena2021'
os.environ['VENDOHM_API_KEY'] = '8c7bed330a4d430282da57e9b517b5dd'
os.environ["VENDOHM_HTTPS_PROXY"] = "http://127.0.0.1:3128"

# LivePos
os.environ['LIVE_POS_PROD_USER'] = 'ws_livepos_tao'
os.environ['LIVE_POS_PROD_PASSWORD'] = 'asdfhu88d'

# Denver / Oracle Databases
os.environ['DENVER_PROD_P219_TAO'] = 'DENVER_ASSETTRADING/b07xtSyq2QBzjc2VGFBjw=doX@P219'
os.environ['DENVER_PROD_P219_AOP'] = 'DENVER_ACCESS_AOP/KuWwFKKNAr5IdmBN=bQEXBCYF@P219'
os.environ['DENVER_CLONE_PROD_P218_BO'] = 'DENVER_ACCESS_BO/RTLDwCkpdFB9Gs5710Q1FqeS=@P218'



