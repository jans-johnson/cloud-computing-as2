"""
Music Subscription Web App - AWS Architecture (us-east-1)

Request Flow:
1. User Browser loads static site from S3 (as2-music-frontend-s4073740).
2. In-page selector picks one of three backends:
   a. Backend 1 (EC2): Browser -> EC2 NGINX :80 -> Gunicorn/Flask :8080
   b. Backend 2 (ECS): Browser -> ALB :80 -> Target Group :8080 -> Fargate task :8080
      (Fargate pulls container image from ECR)
   c. Backend 3 (Serverless): Browser -> API Gateway (REST) -> Lambda (AuthFn / MusicFn / SubscriptionsFn)
3. All three backends read/write DynamoDB tables: login, music, subscriptions.
4. All three backends call S3 (artist images) to generate pre-signed URLs.
5. Browser fetches artist images directly from S3 via pre-signed URL.
6. IAM LabRole is assumed by EC2 instance profile, ECS task role, and Lambda execution role.
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS, ElasticContainerServiceService, Lambda
from diagrams.aws.database import Dynamodb
from diagrams.aws.network import ALB, APIGateway
from diagrams.aws.storage import S3
from diagrams.aws.compute import ECR
from diagrams.onprem.client import User

graph_attr = {
    "fontsize": "18",
    "label": "Music Subscription Web App - AWS Architecture (us-east-1)",
    "labelloc": "t",
    "rankdir": "LR",
    "splines": "ortho",
    "pad": "0.5",
    "nodesep": "0.6",
    "ranksep": "1.2",
}

with Diagram("", filename="architecture", outformat="png", show=False, graph_attr=graph_attr):

    browser = User("User Browser")

    with Cluster("Frontend\n(S3 Static Hosting)"):
        frontend = S3("as2-music-frontend-s4073740\n[Static site; in-page selector\nchooses one of the 3 backends]")

    with Cluster("Backend 1: EC2"):
        nginx = EC2("NGINX :80\n(reverse proxy)")
        flask = EC2("Gunicorn/Flask :8080")
        nginx >> Edge(label=":8080") >> flask

    with Cluster("Backend 2: ECS / Fargate"):
        alb = ALB("ALB :80")
        ecr = ECR("ECR\nmusic-app")
        with Cluster("ECS Cluster: music-app-cluster"):
            ecs_svc = ECS("music-app-service\n(Fargate :8080)")
        alb >> Edge(label="Target Group :8080") >> ecs_svc
        ecr >> Edge(style="dashed", label="image pull") >> ecs_svc

    with Cluster("Backend 3: API Gateway + Lambda"):
        apigw = APIGateway("API Gateway\nGET / POST / DELETE")
        fn_auth = Lambda("AuthFn")
        fn_music = Lambda("MusicFn")
        fn_subs = Lambda("SubscriptionsFn")
        apigw >> fn_auth
        apigw >> fn_music
        apigw >> fn_subs

    with Cluster("Data & Storage (Shared)"):
        dynamo = Dynamodb(
            "DynamoDB\n"
            "• login (PK: email)\n"
            "• music (PK: artist, SK: title_album;\n"
            "  GSI title-artist-index; LSI artist-year-index)\n"
            "• subscriptions (PK: email, SK: song_id;\n"
            "  inverted GSI PK: song_id / SK: email)"
        )
        s3_images = S3("S3: artist-images\n(Block Public Access ON;\npre-signed URLs only)")

    # Browser -> frontend
    browser >> Edge(label="loads static site") >> frontend

    # Browser -> three backends
    browser >> Edge(label="HTTPS/HTTP REST") >> nginx
    browser >> Edge(label="HTTPS/HTTP REST") >> alb
    browser >> Edge(label="HTTPS/HTTP REST") >> apigw

    # Backends -> DynamoDB
    flask >> Edge(label="Query/PutItem/DeleteItem") >> dynamo
    ecs_svc >> Edge(label="Query/PutItem/DeleteItem") >> dynamo
    fn_auth >> dynamo
    fn_music >> dynamo
    fn_subs >> dynamo

    # Backends -> S3 artist images (pre-signed URL generation)
    flask >> Edge(label="GeneratePresignedUrl") >> s3_images
    ecs_svc >> Edge(label="GeneratePresignedUrl") >> s3_images
    fn_auth >> s3_images
    fn_music >> s3_images
    fn_subs >> s3_images

    # Browser -> S3 artist images via pre-signed URL
    browser >> Edge(style="dashed", label="pre-signed URL") >> s3_images


