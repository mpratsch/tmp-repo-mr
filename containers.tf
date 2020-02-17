##########################################
# ECS Cluster
##########################################
data "aws_ecs_cluster" "ecs_cluster" {
  cluster_name = "CCoE-Internal-Monitoring"
}

data "aws_security_groups" "ec2InstanceSecGroup" {
  tags = {
    terraform = "get_reference_for_used_security_group"
  }
}

# Get the VPC id
data "aws_vpc" "main_vpc" {
  id = "vpc-xxxxxxxxxxxxxxxxx"
}
#data "aws_instances" "ecs_cluster_ec2" {
#  instance_tags = {
#      terraform = "aws_lb_target_group_attachment"
#  }
#}
#  ServiceDiscoveryNamespace:
#    Type: AWS::ServiceDiscovery::PrivateDnsNamespace
#    Properties:
#      Name: !Ref Domain
#      Vpc:
#        Fn::ImportValue: !Sub ${EnvironmentName}:VpcId

resource "aws_lb" "app_lb" {
  name               = "CCoE-Testing-WRZRAT-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups     = ["${element(data.aws_security_groups.ec2InstanceSecGroup.ids, 0)}"]
  subnets             = ["subnet-xxxxxxxxxxxxxxxxx","subnet-xxxxxxxxxxxxxxxxx"    ]

  enable_deletion_protection = true

  tags = {
    Owner         = "WRZRAT"
    Environment         = "DEV-WRZAT"
    Contact         = "martina.rath"
    Email         = "martina.rath@xxxx.at"
    Application         = "CCoE Testing WRZRAT"
  }
}

resource "aws_cloudwatch_log_group" "loggroup" {
  name              = "/ecs/CCoE_Testing_WRZRAT/service"
  retention_in_days = 7
}


##########################################
# prometheus-test
##########################################

#-----------------------------------------
# Task Definitions
#-----------------------------------------
resource "aws_ecs_task_definition" "prometheus_test" {
  family                    = "prometheus-test-taskdefinition"
  cpu                       = "256"
  memory                    = "512"
  container_definitions     = "${file("task-definitions/prometheus-test_service.json")}"
  execution_role_arn        = "arn:aws:iam::xxxxxxxxxxxx:role/ecsTaskExecutionRole"
  network_mode              = "host"
  requires_compatibilities  = ["EC2"]
  
  volume {
    name      = "prometheus-data"
    host_path = "/mnt/data/prometheusdata"
  }
  tags = {
    SERVICE_9090_NAME = "prometheus-test"
    Owner         = "WRZRAT"
    Environment         = "DEV-WRZAT"
    Contact         = "martina.rath"
    Email         = "martina.rath@xxxx.at"
    Application         = "CCoE Testing WRZRAT"
  }
  lifecycle {
    create_before_destroy = true
  }
}

#-----------------------------------------
# Service Discovery
#-----------------------------------------
resource "aws_service_discovery_service" "prometheus_test" {
  name = "prometheus-test"

  dns_config {
    namespace_id = "ns-xxxxxxxxxxxxxxxx"
    dns_records {
      ttl  = 60
      type = "SRV"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

#-----------------------------------------
# Ingress Security Group to assign to Instances sec group
#-----------------------------------------
resource "aws_security_group_rule" "prometheus_test_9090_tcp" {
  type        = "ingress"
  description = "prometheus-test - DO NOT DELETE MANUALLY."
  from_port   = 9090
  to_port     = 9090
  protocol    = "tcp"
  cidr_blocks = ["10.225.28.0/24", "10.14.0.0/16","10.197.0.0/16"]
  security_group_id = "${element(data.aws_security_groups.ec2InstanceSecGroup.ids, 0)}"
}

#-----------------------------------------
# Service
#-----------------------------------------
resource "aws_ecs_service" "prometheus_test" {
  name                  = "prometheus-test-service"
  cluster               = "${data.aws_ecs_cluster.ecs_cluster.arn}"
  task_definition       = "${aws_ecs_task_definition.prometheus_test.family}"
  desired_count         = 1
  launch_type           = "EC2"
  service_registries {
    container_name  = "prometheus-test"
    container_port  = "9090"
    registry_arn    = "${aws_service_discovery_service.prometheus_test.arn}"
  }

  load_balancer {
    target_group_arn  = "${aws_lb_target_group.prometheus_test.arn}"
    container_name    = "prometheus-test"
    container_port    = "9090"
  }

  scheduling_strategy   = "REPLICA"
  #lifecycle {
  #  ignore_changes = ["task_definition"]
  #}
  depends_on            = ["aws_iam_role_policy.ecs_CCoE_Testing_WRZRAT_TaskRole_assume_role_policy", "aws_ecs_task_definition.prometheus_test", "aws_lb_target_group.prometheus_test"]
}

#-----------------------------------------
# LoadBalancer settings
#-----------------------------------------
resource "aws_lb_target_group" "prometheus_test" {
  name        = "prometheus-test"
  target_type = "instance"
  port        = 9090
  protocol    = "HTTP"
  vpc_id      = "vpc-xxxxxxxxxxxxxxxxx"
  health_check {
    matcher = "302"
  }
  depends_on = ["aws_lb.app_lb"]
}

resource "aws_lb_target_group_attachment" "prometheus_test" {
  target_group_arn = "${aws_lb_target_group.prometheus_test.arn}"
  #count    = "${length(data.aws_instances.ecs_cluster_ec2.ids)}"
  target_id        = "10.225.28.19"
  port             = 9090
}

resource "aws_lb_listener" "prometheus_test" {
  load_balancer_arn = "${aws_lb.app_lb.arn}"
  port              = "9090"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = "${aws_lb_target_group.prometheus_test.arn}"
  }

  depends_on = [aws_lb_target_group.prometheus_test]
}

##########################################
# alertmanager-test
##########################################

#-----------------------------------------
# Task Definitions
#-----------------------------------------
resource "aws_ecs_task_definition" "alertmanager_test" {
  family                    = "alertmanager-test-taskdefinition"
  cpu                       = "256"
  memory                    = "512"
  container_definitions     = "${file("task-definitions/alertmanager-test_service.json")}"
  execution_role_arn        = "arn:aws:iam::xxxxxxxxxxxx:role/ecsTaskExecutionRole"
  network_mode              = "awsvpc"
  requires_compatibilities  = ["EC2"]
  tags = {
    SERVICE_9093_NAME = "alertmanager-test"
    Owner         = "WRZRAT"
    Environment         = "DEV-WRZAT"
    Contact         = "martina.rath"
    Email         = "martina.rath@xxxx.at"
    Application         = "CCoE Testing WRZRAT"
  }
  lifecycle {
    create_before_destroy = true
  }
}

#-----------------------------------------
# Service Discovery
#-----------------------------------------
resource "aws_service_discovery_service" "alertmanager_test" {
  name = "alertmanager-test"

  dns_config {
    namespace_id = "ns-xxxxxxxxxxxxxxxx"
    dns_records {
      ttl  = 60
      type = "A"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

#-----------------------------------------
# Ingress Security Group to assign to Instances sec group
#-----------------------------------------
resource "aws_security_group_rule" "alertmanager_test_9093_tcp" {
  type        = "ingress"
  description = "alertmanager-test - DO NOT DELETE MANUALLY."
  from_port   = 9093
  to_port     = 9093
  protocol    = "tcp"
  cidr_blocks = ["10.225.28.0/24", "10.14.0.0/16","10.197.0.0/16"]
  security_group_id = "${element(data.aws_security_groups.ec2InstanceSecGroup.ids, 0)}"
}

#-----------------------------------------
# Service
#-----------------------------------------
resource "aws_ecs_service" "alertmanager_test" {
  name                  = "alertmanager-test-service"
  cluster               = "${data.aws_ecs_cluster.ecs_cluster.arn}"
  task_definition       = "${aws_ecs_task_definition.alertmanager_test.family}"
  desired_count         = 1
  launch_type           = "EC2"
  network_configuration {
    #     = ["${aws_security_group_rule.alertmanager_test.id}"]
    security_groups     = "${data.aws_security_groups.ec2InstanceSecGroup.ids}"
    subnets             = ["subnet-xxxxxxxxxxxxxxxxx","subnet-xxxxxxxxxxxxxxxxx"    ]
  }
  service_registries {
    container_name  = "alertmanager-test"
    registry_arn    = "${aws_service_discovery_service.alertmanager_test.arn}"
  }

  load_balancer {
    target_group_arn  = "${aws_lb_target_group.alertmanager_test.arn}"
    container_name    = "alertmanager-test"
    container_port    = "9093"
  }

  scheduling_strategy   = "REPLICA"
  #lifecycle {
  #  ignore_changes = ["task_definition"]
  #}
  depends_on            = ["aws_iam_role_policy.ecs_CCoE_Testing_WRZRAT_TaskRole_assume_role_policy", "aws_ecs_task_definition.alertmanager_test", "aws_lb_target_group.alertmanager_test"]
}

#-----------------------------------------
# LoadBalancer settings
#-----------------------------------------
resource "aws_lb_target_group" "alertmanager_test" {
  name        = "alertmanager-test"
  target_type = "ip"
  port        = 9093
  protocol    = "HTTP"
  vpc_id      = "vpc-xxxxxxxxxxxxxxxxx"
  depends_on = ["aws_lb.app_lb"]
}

resource "aws_lb_target_group_attachment" "alertmanager_test" {
  target_group_arn = "${aws_lb_target_group.alertmanager_test.arn}"
  #count    = "${length(data.aws_instances.ecs_cluster_ec2.private_ips)}"
  target_id        = "10.225.28.30"
  port             = 9093
}

resource "aws_lb_listener" "alertmanager_test" {
  load_balancer_arn = "${aws_lb.app_lb.arn}"
  port              = "9093"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = "${aws_lb_target_group.alertmanager_test.arn}"
  }

  depends_on = [aws_lb_target_group.alertmanager_test]
}

##########################################
# node-exporter-test
##########################################

#-----------------------------------------
# Task Definitions
#-----------------------------------------
resource "aws_ecs_task_definition" "node_exporter_test" {
  family                    = "node-exporter-test-taskdefinition"
  cpu                       = "256"
  memory                    = "512"
  container_definitions     = "${file("task-definitions/node-exporter-test_service.json")}"
  execution_role_arn        = "arn:aws:iam::xxxxxxxxxxxx:role/ecsTaskExecutionRole"
  network_mode              = "bridge"
  requires_compatibilities  = ["EC2"]
  
  volume {
    name      = "node-exporter-proc"
    host_path = "/proc"
  }
  
  volume {
    name      = "node-exporter-sys"
    host_path = "/sys"
  }
  
  volume {
    name      = "node-exporter-rootfs"
    host_path = "/"
  }
  
  volume {
    name      = "node-exporter-docker"
    host_path = "/data/docker"
  }
  
  volume {
    name      = "node-exporter-var-run"
    host_path = "/var/run"
  }
  tags = {
    SERVICE_9100_NAME = "node-exporter-test"
    Owner         = "WRZRAT"
    Environment         = "DEV-WRZAT"
    Contact         = "martina.rath"
    Email         = "martina.rath@xxxx.at"
    Application         = "CCoE Testing WRZRAT"
  }
  lifecycle {
    create_before_destroy = true
  }
}

#-----------------------------------------
# Service Discovery
#-----------------------------------------
resource "aws_service_discovery_service" "node_exporter_test" {
  name = "node-exporter-test"

  dns_config {
    namespace_id = "ns-xxxxxxxxxxxxxxxx"
    dns_records {
      ttl  = 60
      type = "SRV"
    }
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}

#-----------------------------------------
# Ingress Security Group to assign to Instances sec group
#-----------------------------------------
resource "aws_security_group_rule" "node_exporter_test_9100_tcp" {
  type        = "ingress"
  description = "node-exporter-test - DO NOT DELETE MANUALLY."
  from_port   = 9100
  to_port     = 9100
  protocol    = "tcp"
  cidr_blocks = ["10.225.28.0/24", "10.14.0.0/16","10.197.0.0/16"]
  security_group_id = "${element(data.aws_security_groups.ec2InstanceSecGroup.ids, 0)}"
}

#-----------------------------------------
# Service
#-----------------------------------------
resource "aws_ecs_service" "node_exporter_test" {
  name                  = "node-exporter-test-service"
  cluster               = "${data.aws_ecs_cluster.ecs_cluster.arn}"
  task_definition       = "${aws_ecs_task_definition.node_exporter_test.family}"
  desired_count         = 1
  launch_type           = "EC2"
  service_registries {
    container_name  = "node-exporter-test"
    container_port  = "9100"
    registry_arn    = "${aws_service_discovery_service.node_exporter_test.arn}"
  }


  scheduling_strategy   = "DAEMON"
  #lifecycle {
  #  ignore_changes = ["task_definition"]
  #}
  depends_on            = ["aws_iam_role_policy.ecs_CCoE_Testing_WRZRAT_TaskRole_assume_role_policy", "aws_ecs_task_definition.node_exporter_test"]
}


output "loadbalancer_dns_name" {
  value = aws_lb.app_lb.dns_name
}
