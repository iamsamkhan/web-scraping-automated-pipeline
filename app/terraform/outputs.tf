output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.cdn.domain_name
}

output "s3_bucket_papers" {
  description = "S3 bucket for papers"
  value       = aws_s3_bucket.papers.bucket
}

output "s3_bucket_logs" {
  description = "S3 bucket for logs"
  value       = aws_s3_bucket.logs.bucket
}