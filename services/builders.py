class QueryBuilder:
    
    #A korcsoport mezőben megadott adatokat dolgozza fel

    @staticmethod
    def build_age_query(age_ids):
        if not age_ids:
            return ""

        quoted_ids = [f"'{aid}'" for aid in age_ids]
        id_list_str = ", ".join(quoted_ids)
        
        return f"EXISTS {{ MATCH (ag:AgeGroup)-[:READ_BY]->(b) WHERE ag.id IN [{id_list_str}] }}"

    #A korszak mezőben megadott adatokat dolgozza fel

    @staticmethod
    def build_period_query(period_data):
        c_min = period_data.get('custom_min')
        c_max = period_data.get('custom_max')
        
        parts = []
        
        if c_min is not None and str(c_min).strip() != "":
            try:
                val = int(str(c_min).strip())
                parts.append(f"b.original_publication_year >= {val}")
            except ValueError: pass

        if c_max is not None and str(c_max).strip() != "":
            try:
                val = int(str(c_max).strip())
                parts.append(f"b.original_publication_year <= {val}")
            except ValueError: pass

        if parts:
            return f"({' AND '.join(parts)})"
        return ""