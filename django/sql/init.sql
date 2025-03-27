-- Connect to the database
USE fakenews_db;

-- Create user_tool table
CREATE TABLE IF NOT EXISTS user_tool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    method ENUM('GET', 'POST', 'PUT', 'DELETE', 'PATCH') NOT NULL,
    url_template VARCHAR(500) NOT NULL,
    headers JSON,
    default_params JSON,
    data JSON,
    json_payload JSON,
    docstring TEXT,
    target_fields JSON,
    param_mapping JSON,
    FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add index for better performance
CREATE INDEX idx_user_tool_user_id ON user_tool(user_id);
