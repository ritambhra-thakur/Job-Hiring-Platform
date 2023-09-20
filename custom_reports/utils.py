from form.models import AppliedPosition, FormData, OfferLetter


def filter_forma_data(form_data, data):
    # Get all filters
    if "lable" in data and "values" in data:
        departments = data.get("lable").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        form_data = form_data.filter(form_data__department__in=complete_department_list)
    if "lable_net" in data and "values" in data:
        departments = data.get("lable_net").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        form_data = form_data.exclude(form_data__department__in=complete_department_list)
    if "office" in data:
        office = data.get("office").split(",")
        form_data = form_data.filter(form_data__location__0__label__in=office)
    if "office_net" in data:
        office = data.get("office_net").split(",")
        form_data = form_data.exclude(form_data__location__0__label__in=office)
    if "employment_type" in data and "employment_values" in data:
        employment_type = data.get("employment_type").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        form_data = form_data.filter(form_data__employment_type__in=complete_employment_list)
    if "employment_type_net" in data and "employment_values" in data:
        employment_type = data.get("employment_type_net").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        form_data = form_data.exclude(form_data__employment_type__in=complete_employment_list)
    if "level" in data and "level_values" in data:
        level = data.get("level").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        form_data = form_data.filter(form_data__level__in=complete_level_list)
    if "level_net" in data and "level_values" in data:
        level = data.get("level_net").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        form_data = form_data.exclude(form_data__level__in=complete_level_list)
    if "salary_gte" in data and "salary_lte" in data:
        salary_gte = data.get("salary_gte")
        salary_lte = data.get("salary_lte")
        form_data = form_data.filter(form_data__salary__gte=salary_gte, form_data__salary__lte=salary_lte)
    if "salary_lte" in data:
        salary_lte = data.get("salary_lte")
        form_data = form_data.filter(form_data__salary__lte=salary_lte)
    if "salary_gte" in data:
        salary_gte = data.get("salary_gte")
        form_data = form_data.filter(form_data__salary__gte=salary_gte)
    if "salary" in data:
        salary = data.get("salary")
        form_data = form_data.filter(form_data__salary=salary)
    if "open_date_gte" in data and "open_date_lte" in data:
        open_date_gte = data.get("open_date_gte")
        open_date_lte = data.get("open_date_lte")
        form_data = form_data.filter(updated_at__gte=open_date_gte, updated_at__lte=open_date_lte)
    if "open_date_lte" in data:
        open_date_lte = data.get("open_date_lte")
        form_data = form_data.filter(updated_at__lte=open_date_lte)
    if "open_date_gte" in data:
        open_date_gte = data.get("open_date_gte")
        form_data = form_data.filter(updated_at__gte=open_date_gte)
    if "open_date" in data:
        open_date = data.get("open_date")
        form_data = form_data.filter(updated_at=open_date)
    if "status" in data:
        status = data.get("status")
        form_data = form_data.filter(status=status)
    if "status_net" in data:
        status = data.get("status_net")
        form_data = form_data.exclude(status=status)

    return form_data


def filter_applied_position(queryset, data):
    if "lable" in data and "values" in data:
        departments = data.get("lable").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        queryset = queryset.filter(form_data__form_data__department__in=complete_department_list)
    if "lable_net" in data and "values" in data:
        departments = data.get("lable_net").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        queryset = queryset.exclude(form_data__form_data__department__in=complete_department_list)
    if "office" in data:
        office = data.get("office").split(",")
        queryset = queryset.filter(form_data__form_data__location__0__label__in=office)
    if "office_net" in data:
        office = data.get("office_net").split(",")
        queryset = queryset.exclude(form_data__form_data__location__0__label__in=office)
    if "employment_type" in data and "employment_values" in data:
        employment_type = data.get("employment_type").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        queryset = queryset.filter(form_data__form_data__employment_type__in=complete_employment_list)
    if "employment_type_net" in data and "employment_values" in data:
        employment_type = data.get("employment_type_net").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        queryset = queryset.exclude(form_data__form_data__employment_type__in=complete_employment_list)
    if "level" in data and "level_values" in data:
        level = data.get("level").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        queryset = queryset.filter(form_data__form_data__level__in=complete_level_list)
    if "level_net" in data and "level_values" in data:
        level = data.get("level_net").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        queryset = queryset.exclude(form_data__form_data__level__in=complete_level_list)
    if "salary_gte" in data and "salary_lte" in data:
        salary_gte = data.get("salary_gte")
        salary_lte = data.get("salary_lte")
        queryset = queryset.filter(form_data__form_data__salary__gte=salary_gte, form_data__salary__lte=salary_lte)
    if "salary_lte" in data:
        salary_lte = data.get("salary_lte")
        queryset = queryset.filter(form_data__form_data__salary__lte=salary_lte)
    if "salary_gte" in data:
        salary_gte = data.get("salary_gte")
        queryset = queryset.filter(form_data__form_data__salary__gte=salary_gte)
    if "salary" in data:
        salary = data.get("salary")
        queryset = queryset.filter(form_data__form_data__salary=salary)
    if "open_date_gte" in data and "open_date_lte" in data:
        open_date_gte = data.get("open_date_gte")
        open_date_lte = data.get("open_date_lte")
        queryset = queryset.filter(form_data__updated_at__gte=open_date_gte, updated_at__lte=open_date_lte)
    if "open_date_lte" in data:
        open_date_lte = data.get("open_date_lte")
        queryset = queryset.filter(form_data__updated_at__lte=open_date_lte)
    if "open_date_gte" in data:
        open_date_gte = data.get("open_date_gte")
        queryset = queryset.filter(form_data__updated_at__gte=open_date_gte)
    if "open_date" in data:
        open_date = data.get("open_date")
        queryset = queryset.filter(frm_data__updated_at=open_date)
    if "status" in data:
        status = data.get("status")
        queryset = queryset.filter(form_data__status=status)
    if "status_net" in data:
        status = data.get("status_net")
        queryset = queryset.exclude(form_data__status=status)

    return queryset


def filter_offer_letter(queryset, data):
    if "lable" in data and "values" in data:
        departments = data.get("lable").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        queryset = queryset.filter(offered_to__form_data__form_data__department__in=complete_department_list)
    if "lable_net" in data and "values" in data:
        departments = data.get("lable_net").split(",")
        values = data.get("values").split(",")
        complete_department_list = []
        for department, value in zip(departments, values):
            temp = [{"label": department, "value": int(value)}]
            complete_department_list.append(temp)
        queryset = queryset.exclude(offered_to__form_data__form_data__department__in=complete_department_list)
    if "office" in data:
        office = data.get("office").split(",")
        queryset = queryset.filter(offered_to__form_data__form_data__location__0__label__in=office)
    if "office_net" in data:
        office = data.get("office_net").split(",")
        queryset = queryset.exclude(offered_to__form_data__form_data__location__0__label__in=office)
    if "employment_type" in data and "employment_values" in data:
        employment_type = data.get("employment_type").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        queryset = queryset.filter(offered_to__form_data__form_data__employment_type__in=complete_employment_list)
    if "employment_type_net" in data and "employment_values" in data:
        employment_type = data.get("employment_type_net").split(",")
        employment_values = data.get("employment_values").split(",")
        complete_employment_list = []
        for employment, value in zip(employment_type, employment_values):
            temp = [{"label": employment, "value": int(value)}]
            complete_employment_list.append(temp)
        queryset = queryset.exclude(offered_to__form_data__form_data__employment_type__in=complete_employment_list)
    if "level" in data and "level_values" in data:
        level = data.get("level").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        queryset = queryset.filter(offered_to__form_data__form_data__level__in=complete_level_list)
    if "level_net" in data and "level_values" in data:
        level = data.get("level_net").split(",")
        level_values = data.get("level_values").split(",")
        complete_level_list = []
        for i, j in zip(level, level_values):
            temp = [{"label": i, "value": int(j)}]
            complete_level_list.append(temp)
        queryset = queryset.exclude(offered_to__form_data__form_data__level__in=complete_level_list)
    if "salary_gte" in data and "salary_lte" in data:
        salary_gte = data.get("salary_gte")
        salary_lte = data.get("salary_lte")
        queryset = queryset.filter(offered_to__form_data__form_data__salary__gte=salary_gte, form_data__salary__lte=salary_lte)
    if "salary_lte" in data:
        salary_lte = data.get("salary_lte")
        queryset = queryset.filter(offered_to__form_data__form_data__salary__lte=salary_lte)
    if "salary_gte" in data:
        salary_gte = data.get("salary_gte")
        queryset = queryset.filter(offered_to__form_data__form_data__salary__gte=salary_gte)
    if "salary" in data:
        salary = data.get("salary")
        queryset = queryset.filter(offered_to__form_data__form_data__salary=salary)
    if "open_date_gte" in data and "open_date_lte" in data:
        open_date_gte = data.get("open_date_gte")
        open_date_lte = data.get("open_date_lte")
        queryset = queryset.filter(offered_to__form_data__updated_at__gte=open_date_gte, updated_at__lte=open_date_lte)
    if "open_date_lte" in data:
        open_date_lte = data.get("open_date_lte")
        queryset = queryset.filter(offered_to__form_data__updated_at__lte=open_date_lte)
    if "open_date_gte" in data:
        open_date_gte = data.get("open_date_gte")
        queryset = queryset.filter(offered_to__form_data__updated_at__gte=open_date_gte)
    if "open_date" in data:
        open_date = data.get("open_date")
        queryset = queryset.filter(offered_to__frm_data__updated_at=open_date)
    if "status" in data:
        status = data.get("status")
        queryset = queryset.filter(offered_to__form_data__status=status)
    if "status_net" in data:
        status = data.get("status_net")
        queryset = queryset.exclude(offered_to__form_data__status=status)

    return queryset
