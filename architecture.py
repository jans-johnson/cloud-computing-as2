"""
Music Subscription Web App - AWS Architecture (us-east-1)

Request Flow:
1.  User Browser loads static site from S3 (as2-music-frontend-s4073740).
2.  In-page selector picks one of three backends:
    a. Backend 1 (EC2):        Browser -> EC2 NGINX :80 -> Gunicorn/Flask :8080
    b. Backend 2 (ECS/Fargate):Browser -> ALB :80 -> Target Group :8080 -> Fargate task :8080
                                Fargate pulls container image from ECR.
    c. Backend 3 (Serverless): Browser -> API Gateway (REST GET/POST/DELETE)
                                       -> AuthFn / MusicFn / SubscriptionsFn (Lambda)
3.  All three backends read/write DynamoDB tables: login, music, subscriptions.
4.  All three backends call S3 artist-images to generate pre-signed URLs.
5.  Browser fetches artist images directly from S3 via pre-signed URL.
6.  IAM LabRole assumed by EC2 instance profile, ECS task role, Lambda execution role.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS, Lambda, ECR
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import ALB, APIGateway
from diagrams.aws.storage import S3
from diagrams.onprem.client import User

graph_attr = {
    "splines": "ortho",
    "nodesep": "0.8",
    "ranksep": "1.2",
    "fontsize": "11",
    "pad": "0.5",
}

with Diagram(
    "Music Subscription Web App - AWS Architecture (us-east-1)",
    filename="architecture",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    browser = User("User Browser")

    with Cluster("Frontend"):
        frontend = S3("as2-music-frontend-s4073740\n(Static site; in-page selector\nchooses one of the 3 backends)")

    with Cluster("Backends (choose one)"):
        with Cluster("Backend 1: EC2"):
            nginx = EC2("NGINX :80\n(reverse proxy)")
            flask = EC2("Gunicorn/Flask :8080")
            nginx >> Edge(label=":8080 forward") >> flask

        with Cluster("Backend 2: ECS / Fargate"):
            alb = ALB("ALB :80")
            ecr = ECR("ECR: music-app")
            with Cluster("ECS Cluster: music-app-cluster"):
                fargate = ECS("music-app-service\n(Fargate :8080)")
            alb >> Edge(label="Target Group :8080") >> fargate
            ecr >> Edge(style="dashed", label="image pull") >> fargate

        with Cluster("Backend 3: API Gateway + Lambda"):
            apigw = APIGateway("API Gateway\nGET / POST / DELETE")
            fn_auth  = Lambda("AuthFn")
            fn_music = Lambda("MusicFn")
            fn_subs  = Lambda("SubscriptionsFn")
            apigw >> fn_auth
            apigw >> fn_music
            apigw >> fn_subs

    with Cluster("Data & Storage (Shared)"):
        db_login = Dynamodb("login\n(PK email)")
        db_music = Dynamodb("music\n(PK artist / SK title_album)\nGSI title-artist / LSI artist-year")
        db_subs  = Dynamodb("subscriptions\n(PK email / SK song_id)\ninverted GSI song_id/email")
        s3_img   = S3("S3: artist-images\n(Block Public Access ON,\npre-signed URLs only)")


    browser >> Edge(label="loads static site") >> frontend

    # Browser -> three backends
    browser >> Edge(label="HTTPS/HTTP REST") >> nginx
    browser >> Edge(label="HTTPS/HTTP REST") >> alb
    browser >> Edge(label="HTTPS/HTTP REST") >> apigw

    # Backends -> DynamoDB tables
    for node in [flask, fargate, fn_auth, fn_music, fn_subs]:
        node >> Edge(label="Query/Put/Delete") >> db_login
        node >> Edge(label="Query/Put/Delete") >> db_music
        node >> Edge(label="Query/Put/Delete") >> db_subs

    # Backends -> S3 artist images
    for node in [flask, fargate, fn_auth, fn_music, fn_subs]:
        node >> Edge(label="GeneratePresignedUrl") >> s3_img

    # Browser -> S3 artist images via pre-signed URL
    browser >> Edge(style="dashed", label="pre-signed URL") >> s3_img


