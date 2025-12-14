# Makefile

SOLR_URL = "http://localhost:8983/solr/drugs/select"
CURL_GET = curl -s -G
JSON_PRETTY = | jq

.PHONY: help up down logs setup all-queries query-field-boosts query-term-boosts query-independent-boost query-wildcard-fuzzy query-phrase-slop query-query-slop query-proximity-filter query-combined query-pregnancy-eval

help:
	@echo "Available commands:"
	@echo "  make up      - Start the Solr service"
	@echo "  make down    - Stop all services"
	@echo "  make logs    - View Solr logs"
	@echo "  make setup   - Run the one-time Solr setup (adds schema and data)"

# Starts ONLY the solr service in the background
up:
	@echo "Starting Solr service..."
	docker-compose up -d solr

# Stops and removes all containers
down:
	@echo "Stopping all services..."
	docker-compose down

# Follows the logs for the solr service
logs:
	docker-compose logs -f solr

# Runs the 'setup.sh' script inside a temporary container.
setup:
	@echo "Running Solr setup task..."
	docker-compose run --rm solr-setup

all-queries: \
	query-field-boosts \
	query-term-boosts \
	query-independent-boost \
	query-wildcard-fuzzy \
	query-phrase-slop \
	query-query-slop \
	query-proximity-filter \
	query-combined \
	query-pregnancy-eval
	@echo "--- All Section 3 queries executed. ---"

query-field-boosts: ## 3.1: Run query demonstrating Field Boosts (qf)
	@echo "\n--- 3.1: Field Boosts (qf) ---"
	@echo "q=fever & qf=brand_name^3..."
	$(CURL_GET) \
		--data-urlencode "q=fever" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=brand_name^3 generic_name^2 indications_and_usage^1" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-term-boosts: ## 3.2: Run query demonstrating Term Boosts (^)
	@echo "\n--- 3.2: Term Boosts (^) ---"
	@echo "q=fever^2 headache pregnancy^3..."
	$(CURL_GET) \
		--data-urlencode "q=fever^2 headache pregnancy^3" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=indications_and_usage warnings" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-independent-boost: ## 3.3: Run query demonstrating Independent Boost (bf)
	@echo "\n--- 3.3: Independent Boost (bf) ---"
	@echo "q=fever & bf=recip(ms(NOW,effective_time)..."
	$(CURL_GET) \
		--data-urlencode "q=fever" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=text_all" \
		--data-urlencode "bf=recip(ms(NOW,effective_time),3.16e-11,1,1)" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-wildcard-fuzzy: ## 3.4: Run query demonstrating Wildcard (*) and Fuzzy (~)
	@echo "\n--- 3.4: Wildcard (*) and Fuzzy (~) ---"
	@echo "q=warnings:addict* OR generic_name:Ibuprof~1..."
	$(CURL_GET) \
		--data-urlencode "q=warnings:addict* OR generic_name:Ibuprof~1" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=warnings generic_name brand_name" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-phrase-slop: ## 3.5.1: Run query demonstrating Phrase Match w/ Slop (pf, ps)
	@echo "\n--- 3.5.1: Phrase Match w/ Slop (pf, ps) ---"
	@echo "q=ibuprofen allergy & pf=warnings^5... & ps=5"
	$(CURL_GET) \
		--data-urlencode "q=ibuprofen allergy" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=text_all" \
		--data-urlencode "pf=warnings^5 indications_and_usage^3" \
		--data-urlencode "ps=5" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-query-slop: ## 3.5.2: Run query demonstrating Query Phrase Slop (qs)
	@echo "\n--- 3.5.2: Query Phrase Slop (qs) ---"
	@echo "q=\"stomach pain\" & qs=2"
	$(CURL_GET) \
		--data-urlencode "q=\"stomach pain\"" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=indications_and_usage" \
		--data-urlencode "qs=2" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-proximity-filter: ## 3.6: Run query demonstrating Proximity Search ("..."~N)
	@echo "\n--- 3.6: Proximity Search (\"...\"~N) ---"
	@echo "q=warnings:\"liver damage\"~10"
	$(CURL_GET) \
		--data-urlencode "q=warnings:\"liver damage\"~10" \
		--data-urlencode "defType=edismax" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-combined: ## 3.7: Run query demonstrating a combined query
	@echo "\n--- 3.7: Combined Query Example ---"
	@echo "q=(\"generic medicine\"~2 fever^2...) AND (warnings:addict*...)"
	$(CURL_GET) \
		--data-urlencode "q=(\"generic medicine\"~2 fever^2 headache pregnancy^3) AND (warnings:addict* OR warnings:abuse) AND (generic_name:Ibuprof~1 OR generic_name:codien* OR generic_name:asprin~1)" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=brand_name^3 generic_name^2 indications_and_usage^1 warnings" \
		--data-urlencode "fq=product_type:(\"HUMAN PRESCRIPTION DRUG\")" \
		--data-urlencode "fq=purpose:" \
		"$(SOLR_URL)" $(JSON_PRETTY)

query-pregnancy-eval: ## 3.8: Run the full Evaluation Example query
	@echo "\n--- 3.8: Full Evaluation Example (Pregnancy Query) ---"
	@echo "q=(fever^3 OR headache^2) AND (pregnancy^4...)"
	$(CURL_GET) \
		--data-urlencode "q=(fever^3 OR headache^2) AND (pregnancy^4 OR pregnant^4)" \
		--data-urlencode "defType=edismax" \
		--data-urlencode "qf=purpose^4 warnings^3 indications_and_usage^2 brand_name generic_name active_ingredients" \
		--data-urlencode "fq=product_type:(\"HUMAN OTC DRUG\")" \
		--data-urlencode "fq=effective_time:[2024-01-01T00:00:00Z TO NOW]" \
		--data-urlencode "fq=route:ORAL" \
		--data-urlencode "fq=therapeutic_category:("antipyretics" "NSAIDS")" \
		--data-urlencode "bq=warnings:\"pregnancy precautions\"~3^5.0" \
		--data-urlencode "bq=warnings:\"see precautions\"~3^5.0" \
		--data-urlencode "bq=warnings:\"used during pregnancy\"~5^5.0" \
		--data-urlencode "bq=warnings:breastfeeding^4.0" \
		"$(SOLR_URL)" $(JSON_PRETTY)
