"""
Centralized configuration via pydantic-settings.
Reads from .env file and environment variables.

All list-type config fields are stored as comma-separated strings
to avoid pydantic-settings JSON parsing issues with env vars.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> list[str]:
    """Split a comma-separated string into a list, stripping whitespace."""
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Target criteria (stored as CSV strings) ---
    target_roles: str = "Backend Engineer,Data Engineer,Platform Engineer"
    seniority: str = "Mid,Senior"
    locations: str = "Remote,Bangalore,Chennai"
    include_keywords: str = "Python,AWS,distributed systems,Kubernetes,Go,microservices"
    exclude_keywords: str = (
        "unpaid,internship,clearance required,security clearance,TS/SCI"
    )
    min_match_score: float = 0.7

    # --- User profile for frontend ---
    user_skills: str = "Python,Go,AWS,Kubernetes,Docker,PostgreSQL,Redis,Kafka"

    # --- Resume ---
    resume_path: str = "./resume.txt"

    # --- AI Embeddings ---
    embedding_provider: Literal["openai", "gemini", "keyword"] = "keyword"
    embedding_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_embedding_model: str = "text-embedding-004"

    # --- Tier 1: Company slugs (CSV strings) ---
    # Greenhouse: YC companies, VC portfolios, AI startups, top tech
    greenhouse_companies: str = (
        "stripe,gitlab,cloudflare,figma,datadog,twilio,airbnb,coinbase,discord,"
        "anthropic,scale-ai,perplexityai,brex,retool,plaid,gusto,"
        "snyk,webflow,loom,notion,airtable,asana,miro,canva,"
        "chainalysis,dbt-labs,grafana-labs,hashicorp,clickhouse,"
        "mongodb,cockroachlabs,timescale,neon,supabase,"
        "vercel,railway,render,fly-io,netlify,"
        "samsara,toast,ramp,rippling,deel,remote-com,"
        "anduril,palantir,databricks,snowflake,confluent,"
        "elastic,postman,mux,stytch,clerk,"
        "sequoia,a16z,accel,lightspeed,bessemer,"
        "generalcatalyst,greylock,insightpartners,battery,firstround,"
        "sapphire,indexventures,nea,redpoint,"
        "xai,mistral-ai,cohere,cognition-ai,harvey,anysphere,sierra,glean,adept-ai,"
        "runway,elevenlabs,midjourney,fireworks-ai,baseten,together-ai,lambda,"
        "weights-and-biases,huggingface,pinecone,vast-data,groq,cerebras,replit,"
        "windsurf,poolside,magic-ai,reflection-ai,safe-superintelligence,decagon,"
        "mercor,hebbia,factory-ai,lovable,higgsfield,google,meta,microsoft,apple,"
        "amazon,netflix,nvidia,amd,intel,qualcomm,cisco,oracle,ibm,adobe,salesforce,"
        "sap,servicenow,atlassian,jane-street,citadel,citadel-securities,"
        "hudson-river-trading,optiver,jump-trading,imc-trading,drw,tower-research-capital,"
        "two-sigma,de-shaw,five-rings,akuna-capital,susquehanna,virtu-financial,"
        "flow-traders,xr-trading,geneva-trading,belvedere-trading,headlands-technologies,"
        "quantlab,old-mission,transmarket-group,cumberland-drw,wolverine-trading,ctc-trading,"
        "khosla-ventures,hsg,benchmark,cyberstarts,founders-fund,gil-capital,"
        "spark-capital,ribbit-capital,dst-global,foundation-capital,gigafund,"
        "eclipse,altimeter-capital,dfj-growth,union-square-ventures,"
        "a-capital,valor-equity-partners,thrive-capital,sv-angel,point-nine-capital,"
        "a16z-crypto,monolith,greenoaks,menlo-ventures,zhenfund,dragoneer,"
        "entree-capital,felicis-ventures,shunwei-capital,mayfield-fund,"
        "kindred-ventures,fpv,hanabi,conviction-capital,forerunner-ventures,"
        "craft-ventures,bond-capital,coatue,future-ventures,boxgroup,"
        "neo,abstract-ventures,founder-collective,kaszek,idg-capital,"
        "wellington,xyz-venture-capital,qiming-venture-partners,striker-venture-partners,"
        "oak-hc-ft,dcm,addition,notable-capital,laude,crv,gaorong-ventures,"
        "soma-capital,conversion-capital,matrix-partners-china,haystack-ventures,"
        "uncorrelated,"
        "openai,bytedance,wiz,spacex,revolut,chime,monday-com,xiaohongshu,"
        "shein,pony-ai,nubank,celonis,navan,robinhood,biren-technology,"
        "cyera,devoted-health,kuaishou,geek-plus,crusoe-energy,"
        "bloomberg,spotify,snap,yelp,bulb,mobiquity,expensify,free-now,marks-and-spencer,"
        "ef-education-first,contentful,intercom,curve,lego-group,wise,algolia,payfit,sumup,"
        "trainline,deliveroo,collibra,barclays,zalando,ubisoft,klarna,delivery-hero,adnymics,"
        "hive,n26,signavio,wayfair,trivago,babbel,personio,rapidapi,hellofresh,taxfix,blinkist,"
        "soundcloud,pitch,qonto,gorillas,project44,trade-republic,immobilienscout24,clark,forto,"
        "raisin,invision,tipico,container-xchange,sunday,celus,civey,back-market,navvis,e-bot7,"
        "bigpoint,fashion-cloud,uber,booking-com,reaktor,evalan,picnic-technologies,adidas,"
        "verizon-connect,squarespace,etsy,jpmorgan-chase,glovo,swisscom,diet-doctor,bending-spoons,"
        "agentur-loop,blablacar,getaround,deezer,shopee,grab,gojek,ninja-van,foodpanda,zendesk,"
        "circles-life,mercari,fast-retailing,agoda,capital-one,square,shopify,kiwi-com,bolt,"
        "automattic,github,zapier,buffer,canonical,duckduckgo,doist,hotjar,sourcegraph,mozilla,"
        "red-hat,customer-io,assemblyai,brave,ghost,coursera,digitalocean,docker,discourse,"
        "gitbook,khan-academy,toggl,wikimedia,quora,signal,trello,basecamp,toptal,timedoctor,"
        "help-scout,mailerlite,modus-create,clevertech,consensys,datastax,envato,ergeon,feeld,"
        "factorial,headspin,jibble,judge-me,logit-io,nearform,opencraft,pleo,redox,searchapi,"
        "shakacode,shiphero,shogun,softwaremill,stack-exchange,svix,taskade,ted,thorn,trm-labs,tyk"
    )

    # Lever: companies using Lever ATS
    lever_companies: str = (
        "hashicorp,vercel,notion,netlify,tailscale,"
        "benchling,modern-treasury,persona,stytch,vanta,"
        "temporal,prisma,cal-com,"
        "resend,novu,infisical,trigger-dev,inngest,"
        "tinybird,materialize,readwise,raycast,linear,"
        "axiom,highlight,depot,turso,val-town,"
        "kraken,binance,ripple,fireblocks,circle,consensys,alchemy,chainlink-labs,"
        "ava-labs,polygon-labs,offchain-labs,matter-labs,eigen-labs,paradigm,"
        "galaxy-digital,wintermute,falconx,moonpay,ledger,tether,bitgo,uniswap-labs,"
        "dydx-trading,solana-labs,mysten-labs,monad-labs,layerzero-labs,opensea,"
        "khosla-ventures,hsg,benchmark,cyberstarts,founders-fund,gil-capital,"
        "spark-capital,ribbit-capital,dst-global,foundation-capital,gigafund,"
        "eclipse,altimeter-capital,dfj-growth,union-square-ventures,"
        "a-capital,valor-equity-partners,thrive-capital,sv-angel,point-nine-capital,"
        "a16z-crypto,monolith,greenoaks,menlo-ventures,zhenfund,dragoneer,"
        "entree-capital,felicis-ventures,shunwei-capital,mayfield-fund,"
        "kindred-ventures,fpv,hanabi,conviction-capital,forerunner-ventures,"
        "craft-ventures,bond-capital,coatue,future-ventures,boxgroup,"
        "neo,abstract-ventures,founder-collective,kaszek,idg-capital,"
        "wellington,xyz-venture-capital,qiming-venture-partners,striker-venture-partners,"
        "oak-hc-ft,dcm,addition,notable-capital,laude,crv,gaorong-ventures,"
        "soma-capital,conversion-capital,matrix-partners-china,haystack-ventures,"
        "uncorrelated,"
        "openai,bytedance,wiz,spacex,revolut,chime,monday-com,xiaohongshu,"
        "shein,pony-ai,nubank,celonis,navan,robinhood,biren-technology,"
        "cyera,devoted-health,kuaishou,geek-plus,crusoe-energy,"
        "bloomberg,spotify,snap,yelp,bulb,mobiquity,expensify,free-now,marks-and-spencer,"
        "ef-education-first,contentful,intercom,curve,lego-group,wise,algolia,payfit,sumup,"
        "trainline,deliveroo,collibra,barclays,zalando,ubisoft,klarna,delivery-hero,adnymics,"
        "hive,n26,signavio,wayfair,trivago,babbel,personio,rapidapi,hellofresh,taxfix,blinkist,"
        "soundcloud,pitch,qonto,gorillas,project44,trade-republic,immobilienscout24,clark,forto,"
        "raisin,invision,tipico,container-xchange,sunday,celus,civey,back-market,navvis,e-bot7,"
        "bigpoint,fashion-cloud,uber,booking-com,reaktor,evalan,picnic-technologies,adidas,"
        "verizon-connect,squarespace,etsy,jpmorgan-chase,glovo,swisscom,diet-doctor,bending-spoons,"
        "agentur-loop,blablacar,getaround,deezer,shopee,grab,gojek,ninja-van,foodpanda,zendesk,"
        "circles-life,mercari,fast-retailing,agoda,capital-one,square,shopify,kiwi-com,bolt,"
        "automattic,github,zapier,buffer,canonical,duckduckgo,doist,hotjar,sourcegraph,mozilla,"
        "red-hat,customer-io,assemblyai,brave,ghost,coursera,digitalocean,docker,discourse,"
        "gitbook,khan-academy,toggl,wikimedia,quora,signal,trello,basecamp,toptal,timedoctor,"
        "help-scout,mailerlite,modus-create,clevertech,consensys,datastax,envato,ergeon,feeld,"
        "factorial,headspin,jibble,judge-me,logit-io,nearform,opencraft,pleo,redox,searchapi,"
        "shakacode,shiphero,shogun,softwaremill,stack-exchange,svix,taskade,ted,thorn,trm-labs,tyk"
    )

    # Ashby: companies using Ashby ATS
    ashby_companies: str = (
        "ramp,linear,anthropic,mistral,cohere,"
        "huggingface,perplexity,cursor,replit,codeium,"
        "anyscale,modal,together-ai,fireworks-ai,groq,"
        "qdrant,weaviate,pinecone,chroma,zilliz,"
        "dagger,pulumi,encore,fly,railway,"
        "openai,worldquant,alphagrep,irage,quantbox-research,aptus-quant,da-vinci-trading,"
        "qube-research-technologies,millennium,asha-securities,estee-advisors,dolat-capital,"
        "khosla-ventures,hsg,benchmark,cyberstarts,founders-fund,gil-capital,"
        "spark-capital,ribbit-capital,dst-global,foundation-capital,gigafund,"
        "eclipse,altimeter-capital,dfj-growth,union-square-ventures,"
        "a-capital,valor-equity-partners,thrive-capital,sv-angel,point-nine-capital,"
        "a16z-crypto,monolith,greenoaks,menlo-ventures,zhenfund,dragoneer,"
        "entree-capital,felicis-ventures,shunwei-capital,mayfield-fund,"
        "kindred-ventures,fpv,hanabi,conviction-capital,forerunner-ventures,"
        "craft-ventures,bond-capital,coatue,future-ventures,boxgroup,"
        "neo,abstract-ventures,founder-collective,kaszek,idg-capital,"
        "wellington,xyz-venture-capital,qiming-venture-partners,striker-venture-partners,"
        "oak-hc-ft,dcm,addition,notable-capital,laude,crv,gaorong-ventures,"
        "soma-capital,conversion-capital,matrix-partners-china,haystack-ventures,"
        "uncorrelated,"
        "bytedance,wiz,spacex,revolut,chime,monday-com,xiaohongshu,"
        "shein,pony-ai,nubank,celonis,navan,robinhood,biren-technology,"
        "cyera,devoted-health,kuaishou,geek-plus,crusoe-energy,"
        "bloomberg,spotify,snap,yelp,bulb,mobiquity,expensify,free-now,marks-and-spencer,"
        "ef-education-first,contentful,intercom,curve,lego-group,wise,algolia,payfit,sumup,"
        "trainline,deliveroo,collibra,barclays,zalando,ubisoft,klarna,delivery-hero,adnymics,"
        "hive,n26,signavio,wayfair,trivago,babbel,personio,rapidapi,hellofresh,taxfix,blinkist,"
        "soundcloud,pitch,qonto,gorillas,project44,trade-republic,immobilienscout24,clark,forto,"
        "raisin,invision,tipico,container-xchange,sunday,celus,civey,back-market,navvis,e-bot7,"
        "bigpoint,fashion-cloud,uber,booking-com,reaktor,evalan,picnic-technologies,adidas,"
        "verizon-connect,squarespace,etsy,jpmorgan-chase,glovo,swisscom,diet-doctor,bending-spoons,"
        "agentur-loop,blablacar,getaround,deezer,shopee,grab,gojek,ninja-van,foodpanda,zendesk,"
        "circles-life,mercari,fast-retailing,agoda,capital-one,square,shopify,kiwi-com,bolt,"
        "automattic,github,zapier,buffer,canonical,duckduckgo,doist,hotjar,sourcegraph,mozilla,"
        "red-hat,customer-io,assemblyai,brave,ghost,coursera,digitalocean,docker,discourse,"
        "gitbook,khan-academy,toggl,wikimedia,quora,signal,trello,basecamp,toptal,timedoctor,"
        "help-scout,mailerlite,modus-create,clevertech,consensys,datastax,envato,ergeon,feeld,"
        "factorial,headspin,jibble,judge-me,logit-io,nearform,opencraft,pleo,redox,searchapi,"
        "shakacode,shiphero,shogun,softwaremill,stack-exchange,svix,taskade,ted,thorn,trm-labs,tyk"
    )

    # --- Tier 2: Aggregator toggles ---
    enable_remoteok: bool = True
    enable_weworkremotely: bool = True
    enable_hackernews: bool = True
    enable_arbeitnow: bool = True

    # --- New aggregator source toggles ---
    enable_wellfound: bool = True
    enable_ycombinator: bool = True
    enable_builtin: bool = True
    enable_himalayas: bool = True
    enable_dynamite_jobs: bool = True
    enable_remotive: bool = True
    enable_arc_dev: bool = True
    enable_jobspresso: bool = True
    enable_crypto_jobs: bool = True
    enable_ai_jobs: bool = True
    enable_golang_cafe: bool = True
    enable_rustjobs: bool = True
    enable_python_jobs: bool = True
    enable_dribbble: bool = True

    ycombinator_algolia_key: str = (
        "MjBjYjRiMzY0NzdhZWY0NjExY2NhZjYxMGIxYjc2MTAwNWFkNTkwNTc4NjgxYjJiMDRmNjhkMDkxOGMzOWExOXRhZ0ZpbHRlcnM9"
    )

    # --- Tier 3: Career pages ---
    career_pages_json: str = "[]"

    # --- Tier 4: Manual URLs ---
    generate_manual_urls: bool = True

    # --- News ---
    news_sources: str = (
        "hackernews,techcrunch,techmeme,the_information,venturebeat,geekwire,sifted,"
        "crunchbase_news,indie_hackers,producthunt,startup_grind,ycombinator_blog,"
        "first_round_review,openview_blog,a16z_blog,sequoia_blog,bvp_blog,nfx_blog,"
        "signalfire_blog,saastr,both_sides,avc,tomasz_tunguz,feld_thoughts,tech_eu,"
        "eu_startups,siliconangle,alleywatch,finsmes,theverge,wired,arstechnica,cnet,"
        "zdnet,mashable,techradar,digital_trends,slashdot,engadget,gizmodo,fast_company_tech,"
        "pcmag,toms_hardware,android_authority,android_central,macrumors,9to5mac,9to5google,"
        "xda_developers,windows_central,mit_tech_review_ai,bens_bites,the_batch,import_ai,"
        "latent_space,ai_supremacy,the_rundown_ai,superhuman_ai,alphasignal,interconnects,"
        "last_week_in_ai,machine_learning_street_talk,hugging_face_blog,openai_blog,anthropic_news,"
        "deepmind_blog,stability_ai_blog,scale_ai_blog,nvidia_blog,towards_ai,kdnuggets,"
        "infoq,github_blog,stack_overflow_blog,cloudflare_blog,netflix_tech_blog,uber_engineering,"
        "airbnb_engineering,spotify_engineering,meta_engineering,google_developers_blog,aws_news_blog,"
        "microsoft_dev_blogs,stripe_engineering,slack_engineering,linkedin_engineering,"
        "pinterest_engineering,dropbox_tech_blog,discord_engineering,datadog_engineering,"
        "shopify_engineering,cockroach_labs_blog,confluent_blog,planetscale_blog,vercel_blog,"
        "hashicorp_blog,krebs_on_security,the_hacker_news,dark_reading,bleepingcomputer,securityweek,"
        "help_net_security,sans_newsbites,schneier_on_security,threatpost,security_boulevard,"
        "malwarebytes_labs,cisco_talos_blog,mandiant_blog,crowdstrike_blog,stratechery,platformer,"
        "big_technology,semafor_technology,bloomberg_technology,cnbc_technology,fortune_tech,"
        "financial_times_tech,reuters_technology,wsj_technology,axios_pro_rata,dealbook,"
        "protocol_archive,quartz_tech,hashnode,freecodecamp,css_tricks,smashing_magazine,"
        "sitepoint,dzone,hackernoon,codrops,javascript_weekly,python_weekly,golang_weekly,"
        "tldr_newsletter,bytes_dev,devto"
    )
    news_cache_ttl_seconds: int = 300

    # --- Notification ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    notify_from: str = ""
    notify_to: str = ""

    # --- Compliance ---
    user_agent: str = "JobHunter/1.0 (contact: user@example.com)"
    rate_limit_per_second: float = 2.0
    request_timeout: int = 30

    # --- Schedule ---
    crawl_interval_hours: int = 4

    # --- Database ---
    db_path: str = "./data/jobs.db"

    # --- Server ---
    server_host: str = "127.0.0.1"  # Bound to localhost by default for security
    server_port: int = 8000

    # ---- Computed list properties ----

    @property
    def target_roles_list(self) -> list[str]:
        return _split_csv(self.target_roles)

    @property
    def seniority_list(self) -> list[str]:
        return _split_csv(self.seniority)

    @property
    def locations_list(self) -> list[str]:
        return _split_csv(self.locations)

    @property
    def include_keywords_list(self) -> list[str]:
        return _split_csv(self.include_keywords)

    @property
    def exclude_keywords_list(self) -> list[str]:
        return _split_csv(self.exclude_keywords)

    @property
    def user_skills_list(self) -> list[str]:
        return _split_csv(self.user_skills)

    @property
    def greenhouse_companies_list(self) -> list[str]:
        return _split_csv(self.greenhouse_companies)

    @property
    def lever_companies_list(self) -> list[str]:
        return _split_csv(self.lever_companies)

    @property
    def ashby_companies_list(self) -> list[str]:
        return _split_csv(self.ashby_companies)

    @property
    def career_pages(self) -> list[dict]:
        try:
            data = json.loads(self.career_pages_json)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def news_sources_list(self) -> list[str]:
        return _split_csv(self.news_sources)

    @property
    def db_dir(self) -> Path:
        return Path(self.db_path).parent

    @property
    def notifications_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.notify_to)


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
