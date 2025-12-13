package me.project.snowbot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class SnowbotApplication {

	public static void main(String[] args) {
		SpringApplication.run(SnowbotApplication.class, args);
	}

}
