"""
Task Category and Tag Management Views
Handles CRUD operations for task categories and tags
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from accounts.models import TaskCategory, TaskTag


# ============================================================================
# Category Management
# ============================================================================

@login_required
def manageCategories(request: HttpRequest) -> HttpResponse:
    """
    Display all categories for the current user.
    """
    user = request.user
    categories = TaskCategory.objects.filter(
        created_by=user,
        is_deleted=False
    ).order_by('display_order', 'name')
    
    context = {
        'categories': categories
    }
    
    return render(request, 'task/manage_categories.html', context)


@login_required
def addCategory(request: HttpRequest) -> HttpResponse:
    """
    Create a new category.
    """
    if request.method != "POST":
        return HttpResponseRedirect('/manageCategories/')
    
    user = request.user
    
    TaskCategory.objects.create(
        name=request.POST.get('name'),
        description=request.POST.get('description', ''),
        color=request.POST.get('color', '#3B82F6'),
        icon=request.POST.get('icon', ''),
        display_order=request.POST.get('display_order', 0),
        created_by=user
    )
    
    return HttpResponseRedirect('/manageCategories/')


@login_required
def editCategory(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update an existing category.
    """
    if request.method != "POST":
        return HttpResponseRedirect('/manageCategories/')
    
    category = get_object_or_404(TaskCategory, id=id, created_by=request.user)
    
    category.name = request.POST.get('name', category.name)
    category.description = request.POST.get('description', '')
    category.color = request.POST.get('color', category.color)
    category.icon = request.POST.get('icon', '')
    category.display_order = request.POST.get('display_order', category.display_order)
    category.save()
    
    return HttpResponseRedirect('/manageCategories/')


@login_required
def deleteCategory(request: HttpRequest, id: int) -> HttpResponse:
    """
    Soft delete a category.
    """
    category = get_object_or_404(TaskCategory, id=id, created_by=request.user)
    category.is_deleted = True
    category.save()
    
    return HttpResponseRedirect('/manageCategories/')


# ============================================================================
# Tag Management
# ============================================================================

@login_required
def manageTags(request: HttpRequest) -> HttpResponse:
    """
    Display all tags for the current user.
    """
    user = request.user
    tags = TaskTag.objects.filter(created_by=user).order_by('name')
    
    context = {
        'tags': tags
    }
    
    return render(request, 'task/manage_tags.html', context)


@login_required
def addTag(request: HttpRequest) -> HttpResponse:
    """
    Create a new tag.
    """
    if request.method != "POST":
        return HttpResponseRedirect('/manageTags/')
    
    user = request.user
    
    TaskTag.objects.create(
        name=request.POST.get('name'),
        color=request.POST.get('color', '#10B981'),
        created_by=user
    )
    
    return HttpResponseRedirect('/manageTags/')


@login_required
def editTag(request: HttpRequest, id: int) -> HttpResponse:
    """
    Update an existing tag.
    """
    if request.method != "POST":
        return HttpResponseRedirect('/manageTags/')
    
    tag = get_object_or_404(TaskTag, id=id, created_by=request.user)
    
    tag.name = request.POST.get('name', tag.name)
    tag.color = request.POST.get('color', tag.color)
    tag.save()
    
    return HttpResponseRedirect('/manageTags/')


@login_required
def deleteTag(request: HttpRequest, id: int) -> HttpResponse:
    """
    Delete a tag.
    """
    tag = get_object_or_404(TaskTag, id=id, created_by=request.user)
    tag.delete()
    
    return HttpResponseRedirect('/manageTags/')
