import streamlit as st
import requests
import pandas as pd
from datetime import datetime

LEGACY_PREFIX = "downloaded_pdf_"


def clean_filename(filename: str) -> str:
    """Remove the legacy prefix from filenames for display."""
    if filename and filename.startswith(LEGACY_PREFIX):
        return filename[len(LEGACY_PREFIX):]
    return filename

st.set_page_config(page_title="PDF Processor", page_icon="📄", layout="wide")

st.title("📄 PDF Processor Dashboard")

# API base URL
API_BASE_URL = "http://localhost:8000"

def get_all_pdfs():
    """Fetch all processed PDFs from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/pdfs")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching PDFs: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_stats():
    """Fetch processing statistics from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/stats")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException:
        return None

def trigger_conversion(uri):
    """Trigger conversion for a specific PDF."""
    try:
        response = requests.post(f"{API_BASE_URL}/convert/{uri}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def delete_pdf(uri):
    """Delete a PDF record by URI."""
    try:
        response = requests.delete(f"{API_BASE_URL}/pdfs/{uri}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def trigger_extraction(paper_id):
    """Trigger extraction for a specific PDF."""
    try:
        response = requests.post(f"{API_BASE_URL}/extract/{paper_id}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_extraction_results(paper_id):
    """Get extraction results for a specific PDF."""
    try:
        response = requests.get(f"{API_BASE_URL}/extract/{paper_id}")
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def get_extraction_template():
    """Get the extraction template structure."""
    try:
        response = requests.get(f"{API_BASE_URL}/extract/template")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

def trigger_selective_extraction(paper_id, selected_fields, selected_models, selected_size):
    """Trigger selective extraction for a specific PDF."""
    try:
        payload = {
            "selected_fields": selected_fields,
            "selected_models": selected_models,
            "selected_size": selected_size
        }
        response = requests.post(f"{API_BASE_URL}/extract/{paper_id}/selective", json=payload)
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["📋 PDF List", "➕ Process New PDF", "📊 Statistics", "🔄 Conversion Queue", "🔍 Extraction Queue", "🎯 Selective Extraction"])

if page == "📋 PDF List":
    st.header("Processed PDFs")
    
    # Add refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Fetch all PDFs
    pdf_data = get_all_pdfs()
    
    if pdf_data and pdf_data.get("pdfs"):
        pdfs = pdf_data["pdfs"]
        st.success(f"Found {pdf_data['count']} processed PDFs")
        
        # Convert to DataFrame for better display
        df_data = []
        for pdf in pdfs:
            # Determine conversion status
            is_converted = pdf.get("is_converted", False)
            conversion_status = "✅ Converted" if is_converted else "⏳ Pending"
            if pdf.get("conversion_error"):
                conversion_status = "❌ Failed"
            elif pdf.get("conversion_started_at") and not is_converted:
                conversion_status = "🔄 Converting"
            
            # Determine extraction status
            is_extracted = pdf.get("is_extracted", False)
            extraction_status = "✅ Extracted" if is_extracted else "⏳ Pending"
            if pdf.get("extraction_error"):
                extraction_status = "❌ Failed"
            elif pdf.get("extraction_started_at") and not is_extracted:
                extraction_status = "🔄 Extracting"
            elif not is_converted:
                extraction_status = "⏸ Waiting for conversion"
            
            df_data.append({
                "ID": pdf.get("id", ""),
                "URI": pdf.get("uri", "")[:50] + "..." if len(pdf.get("uri", "")) > 50 else pdf.get("uri", ""),
                "Filename": clean_filename(pdf.get("filename", "")),
                "File Size (KB)": round(pdf.get("file_size", 0) / 1024, 2) if pdf.get("file_size") else 0,
                "Status": "✅ Success" if pdf.get("status") == "success" else "❌ Error",
                "Downloaded": "✅ Yes" if pdf.get("is_downloaded") else "❌ No",
                "Converted": conversion_status,
                "Processed At": pdf.get("processed_at", "")[:19] if pdf.get("processed_at") else ""
            })
        
        df = pd.DataFrame(df_data)
        
        # Display the dataframe
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "URI": st.column_config.TextColumn("URI", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Downloaded": st.column_config.TextColumn("Downloaded", width="small"),
                "Converted": st.column_config.TextColumn("Converted", width="medium"),
            }
        )
        
        # Show detailed view for selected PDF
        st.subheader("PDF Details")
        selected_indices = st.selectbox(
            "Select a PDF to view details:",
            options=range(len(pdfs)),
            format_func=lambda i: f"{clean_filename(pdfs[i].get('filename', 'Unknown'))} - {pdfs[i].get('uri', '')[:30]}..."
        )
        
        if selected_indices is not None:
            selected_pdf = pdfs[selected_indices]
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**ID:**", selected_pdf.get("id"))
                st.write("**Filename:**", clean_filename(selected_pdf.get("filename")))
                st.write("**File Size:**", f"{selected_pdf.get('file_size', 0):,} bytes")
                st.write("**Content Type:**", selected_pdf.get("content_type"))
                st.write("**Status:**", selected_pdf.get("status"))
                st.write("**Downloaded:**", "Yes" if selected_pdf.get("is_downloaded") else "No")
                
            with col2:
                st.write("**Converted:**", "✅ Yes" if selected_pdf.get("is_converted") else "❌ No")
                st.write("**Extracted:**", "✅ Yes" if selected_pdf.get("is_extracted") else "❌ No")
                st.write("**Processed At:**", selected_pdf.get("processed_at"))
                
                # Conversion details
                if selected_pdf.get("conversion_started_at"):
                    st.write("**Conversion Started:**", selected_pdf.get("conversion_started_at")[:19])
                if selected_pdf.get("conversion_completed_at"):
                    st.write("**Conversion Completed:**", selected_pdf.get("conversion_completed_at")[:19])
                if selected_pdf.get("conversion_error"):
                    st.write("**Conversion Error:**", selected_pdf.get("conversion_error"))
                
                # Extraction details
                if selected_pdf.get("extraction_started_at"):
                    st.write("**Extraction Started:**", selected_pdf.get("extraction_started_at")[:19])
                if selected_pdf.get("extraction_completed_at"):
                    st.write("**Extraction Completed:**", selected_pdf.get("extraction_completed_at")[:19])
                if selected_pdf.get("extraction_error"):
                    st.write("**Extraction Error:**", selected_pdf.get("extraction_error"))
                    
                if selected_pdf.get("text_file_path"):
                    st.write("**Text File:**", selected_pdf.get("text_file_path"))
                if selected_pdf.get("images_folder_path"):
                    st.write("**Images Folder:**", selected_pdf.get("images_folder_path"))
                if selected_pdf.get("extraction_file_path"):
                    st.write("**Extraction File:**", selected_pdf.get("extraction_file_path"))
                
                if selected_pdf.get("error_message"):
                    st.write("**Error:**", selected_pdf.get("error_message"))
            
            st.write("**Full URI:**", selected_pdf.get("uri"))
            st.write("**File Path:**", selected_pdf.get("file_path"))
            
            # Action buttons section
            action_buttons_shown = False
            
            # Add manual conversion trigger button
            if (selected_pdf.get("is_downloaded") and 
                selected_pdf.get("status") == "success" and 
                not selected_pdf.get("is_converted") and 
                not selected_pdf.get("conversion_error")):
                
                if not action_buttons_shown:
                    st.markdown("---")
                    st.subheader("🔧 Actions")
                    action_buttons_shown = True
                    
                if st.button("🔄 Trigger Conversion", key=f"convert_{selected_pdf.get('id')}"):
                    with st.spinner("Triggering conversion..."):
                        response = trigger_conversion(selected_pdf.get("uri"))
                        if response and response.status_code == 200:
                            st.success("Conversion triggered successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to trigger conversion")
            
            # Add manual extraction trigger button
            if (selected_pdf.get("is_converted") and 
                not selected_pdf.get("is_extracted") and 
                not selected_pdf.get("extraction_error")):
                
                if not action_buttons_shown:
                    st.markdown("---")
                    st.subheader("🔧 Actions")
                    action_buttons_shown = True
                    
                if st.button("🔍 Trigger Extraction", key=f"extract_{selected_pdf.get('id')}"):
                    with st.spinner("Triggering extraction..."):
                        response = trigger_extraction(selected_pdf.get("id"))
                        if response and response.status_code == 200:
                            st.success("Extraction triggered successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to trigger extraction")
            
            # Show extraction results button if available
            if selected_pdf.get("is_extracted"):
                if not action_buttons_shown:
                    st.markdown("---")
                    st.subheader("🔧 Actions")
                    action_buttons_shown = True
                    
                if st.button("📄 View Extraction Results", key=f"view_extract_{selected_pdf.get('id')}"):
                    with st.spinner("Loading extraction results..."):
                        response = get_extraction_results(selected_pdf.get("id"))
                        if response and response.status_code == 200:
                            extraction_data = response.json()
                            
                            st.markdown("---")
                            st.subheader("📄 Extraction Results")
                            
                            # Get extraction data
                            extract_info = extraction_data.get("extraction_data", {})
                            summaries = extract_info.get("summaries", [])
                            questions = extract_info.get("questions", [])
                            
                            # Show overview metrics
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Models Used", len(set([s.get('model') for s in summaries])))
                            with col2:
                                st.metric("Summaries", len(summaries))
                            with col3:
                                st.metric("Questions Answered", len(questions))
                            with col4:
                                unique_questions = len(set([q.get('question', '').split('?')[0] + '?' for q in questions]))
                                st.metric("Unique Questions", unique_questions)
                            
                            # Show summaries
                            if summaries:
                                st.subheader("📝 Summaries by Model")
                                for summary in summaries:
                                    model_name = summary.get('model', 'Unknown Model')
                                    summary_text = summary.get('summary', 'No summary available')
                                    
                                    with st.expander(f"🤖 {model_name} Summary"):
                                        st.write(summary_text)
                            
                            # Show questions and answers
                            if questions:
                                st.subheader("❓ Questions & Answers")
                                
                                # Get predefined questions from the API
                                template = get_extraction_template()
                                if template and template.get("questions"):
                                    predefined_questions = template["questions"]
                                else:
                                    predefined_questions = []
                                    st.warning("Could not load questions from API")
                                
                                # Group answers by question
                                question_groups = {}
                                
                                # The structure is: {"model": "model_name", "question": "answer_text"}
                                # Since we have model x question combinations, we need to group them properly
                                
                                # First, let's understand how many questions per model we have
                                models_used = list(set([q.get('model') for q in questions]))
                                questions_per_model = len(questions) // len(models_used) if models_used else 0
                                
                                for i, q_item in enumerate(questions):
                                    model = q_item.get('model', 'Unknown Model')
                                    answer = q_item.get('question', 'No answer available')
                                    
                                    # Calculate which question this is based on the pattern:
                                    # Each model answers all questions in sequence
                                    question_index = i % len(predefined_questions)
                                    question_text = predefined_questions[question_index]
                                    
                                    if question_text not in question_groups:
                                        question_groups[question_text] = []
                                    
                                    question_groups[question_text].append({
                                        'model': model,
                                        'answer': answer
                                    })
                                
                                # Display questions and answers
                                for question_text, answers in question_groups.items():
                                    with st.expander(f"❓ {question_text}"):
                                        for answer_item in answers:
                                            model_name = answer_item['model']
                                            answer_text = answer_item['answer']
                                            
                                            st.write(f"**🤖 {model_name}:**")
                                            st.write(answer_text)
                                            if len(answers) > 1:  # Only show separator if multiple answers
                                                st.write("---")
                                
                        else:
                            st.error("Failed to load extraction results")
            
            # Add delete section with confirmation
            st.markdown("---")
            st.subheader("🗑 Danger Zone")
            
            # Initialize session state for delete confirmation
            delete_key = f"confirm_delete_{selected_pdf.get('id')}"
            if delete_key not in st.session_state:
                st.session_state[delete_key] = False
            
            if not st.session_state[delete_key]:
                if st.button("🗑 Delete PDF", key=f"delete_{selected_pdf.get('id')}", type="secondary"):
                    st.session_state[delete_key] = True
                    st.rerun()
            else:
                # Build list of files that will be deleted
                files_to_delete = []
                if selected_pdf.get("file_path"):
                    files_to_delete.append("📄 Original PDF file")
                if selected_pdf.get("text_file_path"):
                    files_to_delete.append("📝 Extracted text file")
                if selected_pdf.get("images_folder_path"):
                    files_to_delete.append("🖼️ Extracted images folder")
                
                file_list = "\n• ".join(files_to_delete) if files_to_delete else "No files to delete"
                
                st.warning(f"""⚠️ **Are you sure you want to delete this PDF?**

**Filename:** {clean_filename(selected_pdf.get('filename'))}
**File Size:** {selected_pdf.get('file_size', 0):,} bytes

**The following will be permanently deleted:**
• {file_list}
• Database record

**This action cannot be undone!**""")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Yes, Delete", key=f"confirm_yes_{selected_pdf.get('id')}", type="primary"):
                        with st.spinner("Deleting PDF..."):
                            response = delete_pdf(selected_pdf.get("uri"))
                            if response and response.status_code == 200:
                                st.success("PDF deleted successfully!")
                                # Reset session state
                                st.session_state[delete_key] = False
                                st.rerun()
                            else:
                                st.error("Failed to delete PDF")
                                st.session_state[delete_key] = False
                
                with col2:
                    if st.button("❌ Cancel", key=f"confirm_no_{selected_pdf.get('id')}"):
                        st.session_state[delete_key] = False
                        st.rerun()
            
    else:
        st.info("No PDFs have been processed yet. Use the 'Process New PDF' page to add some!")

elif page == "➕ Process New PDF":
    st.header("Process New PDF")
    
    user_input = st.text_input("Enter PDF URL:", placeholder="https://example.com/document.pdf")
    
    if st.button("Process PDF"):
        if user_input:
            with st.spinner("Processing PDF..."):
                try:
                    response = requests.post(f"{API_BASE_URL}/pdfs", json={"uri": user_input})
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success("PDF processed successfully!")
                        
                        # Show processing results
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Status:**", "✅ Success" if result.get("is_pdf") else "❌ Not a PDF")
                            st.write("**Downloaded:**", "✅ Yes" if result.get("downloaded") else "❌ No")
                            st.write("**From Cache:**", "Yes" if result.get("from_cache") else "No")
                        
                        with col2:
                            st.write("**Converted:**", "✅ Yes" if result.get("is_converted") else "⏳ Queued")
                            st.write("**Conversion Status:**", result.get("conversion_status", "Unknown"))
                            if result.get("file_size"):
                                st.write("**File Size:**", f"{result.get('file_size'):,} bytes")
                            if result.get("file_path"):
                                st.write("**Saved to:**", result.get("file_path"))
                        
                        st.write("**Message:**", result.get("message"))
                        
                        # Show conversion info if available
                        if result.get("conversion_status") == "queued":
                            st.info("🔄 PDF has been queued for conversion. Check back in a few minutes!")
                        
                    else:
                        st.error(f"Error: {response.status_code} - {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection error: {str(e)}")
        else:
            st.warning("Please enter a PDF URL")

elif page == "📊 Statistics":
    st.header("Processing Statistics")
    
    stats = get_stats()
    
    if stats:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Total Processed", stats.get("total_processed", 0))
        
        with col2:
            st.metric("Successful Downloads", stats.get("successful_downloads", 0))
        
        with col3:
            st.metric("Converted PDFs", stats.get("converted_pdfs", 0))
        
        with col4:
            st.metric("Extracted PDFs", stats.get("extracted_pdfs", 0))
        
        with col5:
            st.metric("Pending Extraction", stats.get("pending_extraction", 0))
        
        with col6:
            st.metric("Failed Attempts", stats.get("failed_attempts", 0))
        
        # Additional metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_size_mb = stats.get("total_file_size_bytes", 0) / (1024 * 1024)
            st.metric("Total Size (MB)", f"{total_size_mb:.2f}")
        
        # Success rate
        total = stats.get("total_processed", 0)
        successful = stats.get("successful_downloads", 0)
        if total > 0:
            success_rate = (successful / total) * 100
            with col2:
                st.metric("Download Success Rate", f"{success_rate:.1f}%")
        
        # Conversion rate
        downloaded = stats.get("successful_downloads", 0)
        converted = stats.get("converted_pdfs", 0)
        if downloaded > 0:
            conversion_rate = (converted / downloaded) * 100
            with col3:
                st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
        
        # Extraction rate
        extracted = stats.get("extracted_pdfs", 0)
        if converted > 0:
            extraction_rate = (extracted / converted) * 100
            st.metric("Extraction Rate", f"{extraction_rate:.1f}%")
            
            # Progress bars
            st.subheader("Progress Overview")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write("**Download Success Rate**")
                st.progress(success_rate / 100 if total > 0 else 0)
            with col2:
                st.write("**Conversion Rate**")
                st.progress(conversion_rate / 100)
            with col3:
                st.write("**Extraction Rate**")
                st.progress(extraction_rate / 100)
    else:
        st.error("Unable to fetch statistics")

elif page == "🔄 Conversion Queue":
    st.header("Conversion Queue Management")
    
    # Process conversion queue button
    if st.button("🚀 Process All Pending Conversions"):
        with st.spinner("Processing conversion queue..."):
            try:
                response = requests.post(f"{API_BASE_URL}/convert/process-queue")
                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Queue processed successfully!"))
                    
                    # Show results if available
                    if result.get("results"):
                        st.subheader("Conversion Results")
                        for res in result["results"]:
                            if res.get("success"):
                                st.success(f"✅ {res.get('uri')}: {res.get('message')}")
                            else:
                                st.error(f"❌ {res.get('uri')}: {res.get('error')}")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
    
    st.markdown("---")
    st.info("Use this page to manually trigger conversion of all pending PDFs. The system automatically converts PDFs when they are first added, but you can use this if any conversions failed or were missed.")

elif page == "🔍 Extraction Queue":
    st.header("Extraction Queue Management")
    
    # Process extraction queue button
    if st.button("🚀 Process All Pending Extractions"):
        with st.spinner("Processing extraction queue..."):
            try:
                response = requests.post(f"{API_BASE_URL}/extract/process-queue")
                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Queue processed successfully!"))
                    
                    # Show results if available
                    if result.get("results"):
                        st.subheader("Extraction Results")
                        for res in result["results"]:
                            if res.get("success"):
                                st.success(f"✅ {res.get('uri')}: {res.get('message')}")
                                if res.get("extracted_sections"):
                                    st.info(f"   📄 Extracted {res.get('extracted_sections')} sections and {res.get('extracted_entities', 0)} entities")
                            else:
                                st.error(f"❌ {res.get('uri')}: {res.get('error')}")
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
    
    st.markdown("---")
    st.info("Use this page to manually trigger extraction of all converted PDFs. The system automatically extracts PDFs after they are converted, but you can use this if any extractions failed or were missed.")

elif page == "🎯 Selective Extraction":
    st.header("Selective Field Extraction")
    
    # Get extraction template
    template = get_extraction_template()
    if not template:
        st.error("Could not load extraction template from API")
        st.stop()
    
    # Get list of converted PDFs for selection
    pdf_data = get_all_pdfs()
    if not pdf_data or not pdf_data.get("pdfs"):
        st.warning("No PDFs available. Please process some PDFs first.")
        st.stop()
    
    # Filter for converted PDFs
    converted_pdfs = [pdf for pdf in pdf_data["pdfs"] if pdf.get("is_converted")]
    if not converted_pdfs:
        st.warning("No converted PDFs available. Please convert some PDFs first.")
        st.stop()
    
    # PDF Selection
    st.subheader("📄 Select PDF")
    selected_pdf_idx = st.selectbox(
        "Choose a PDF for selective extraction:",
        options=range(len(converted_pdfs)),
        format_func=lambda i: f"{clean_filename(converted_pdfs[i].get('filename', 'Unknown'))} (ID: {converted_pdfs[i].get('id')})"
    )
    
    if selected_pdf_idx is not None:
        selected_pdf = converted_pdfs[selected_pdf_idx]
        
        st.info(f"**Selected PDF:** {clean_filename(selected_pdf.get('filename'))}")
        st.write(f"**URI:** {selected_pdf.get('uri')}")
        
        # Model Selection
        st.subheader("🤖 Select Models")
        available_models = template.get("models", [])
        
        if not available_models:
            st.error("No models available in template")
            st.stop()
        
        # Create model selection with details
        model_options = []
        for model in available_models:
            model_name = model.get("name")
            context_size = model.get("context_size", "Unknown")
            description = model.get("description", "")
            model_options.append({
                "name": model_name,
                "display": f"{model_name} (Context: {context_size:,} tokens)",
                "context_size": context_size,
                "description": description
            })
        
        # Multi-select for models
        selected_model_names = st.multiselect(
            "Select models to use for extraction:",
            options=[model["name"] for model in model_options],
            default=[model_options[0]["name"]] if model_options else [],
            format_func=lambda name: next(model["display"] for model in model_options if model["name"] == name)
        )
        
        if not selected_model_names:
            st.warning("Please select at least one model.")
            st.stop()
        
        # Size Selection
        st.subheader("📏 Select Size")
        size_limits = template.get("size_limits", {})
        size_options = ["small", "medium", "large"]
        
        selected_size = st.selectbox(
            "Choose extraction size:",
            options=size_options,
            index=1,  # Default to medium
            format_func=lambda size: f"{size.title()} ({size_limits.get(size, 'Unknown'):,} chars)" if size_limits.get(size) else size.title()
        )
        
        # Field Selection
        st.subheader("🎯 Select Fields to Extract")
        
        fields = template.get("fields", [])
        if not fields:
            st.error("No fields available in template")
            st.stop()
        
        # Separate fields by type
        summary_fields = [field for field in fields if field.get("kind") == "summary"]
        question_fields = [field for field in fields if field.get("kind") == "question"]
        
        selected_fields = []
        
        # Summary fields section
        if summary_fields:
            st.write("**📝 Summary Fields:**")
            for field in summary_fields:
                field_title = field.get("title")
                field_description = field.get("description", "")
                supported_sizes = field.get("supported_size", [])
                
                # Check if current size is supported
                size_supported = selected_size in supported_sizes
                help_text = f"{field_description}"
                if not size_supported:
                    help_text += f" (⚠️ {selected_size} size not supported - supported: {', '.join(supported_sizes)})"
                
                if st.checkbox(
                    field_title.replace("_", " ").title(),
                    key=f"summary_{field_title}",
                    help=help_text,
                    disabled=not size_supported
                ):
                    if size_supported:
                        selected_fields.append(field_title)
        
        # Question fields section
        if question_fields:
            st.write("**❓ Question Fields:**")
            for field in question_fields:
                field_title = field.get("title")
                supported_sizes = field.get("supported_size", [])
                
                # Check if current size is supported
                size_supported = selected_size in supported_sizes
                help_text = f"Answer to: {field_title}"
                if not size_supported:
                    help_text += f" (⚠️ {selected_size} size not supported - supported: {', '.join(supported_sizes)})"
                
                if st.checkbox(
                    field_title,
                    key=f"question_{field_title}",
                    help=help_text,
                    disabled=not size_supported
                ):
                    if size_supported:
                        selected_fields.append(field_title)
        
        # Show selection summary
        if selected_fields:
            st.subheader("📋 Selection Summary")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Selected Fields", len(selected_fields))
            with col2:
                st.metric("Selected Models", len(selected_model_names))
            with col3:
                estimated_extractions = len(selected_fields) * len(selected_model_names)
                st.metric("Total Extractions", estimated_extractions)
            
            # Show selected fields
            st.write("**Selected Fields:**")
            summary_selected = [f for f in selected_fields if f in [field["title"] for field in summary_fields]]
            question_selected = [f for f in selected_fields if f in [field["title"] for field in question_fields]]
            
            if summary_selected:
                st.write(f"📝 Summaries: {', '.join([f.replace('_', ' ').title() for f in summary_selected])}")
            if question_selected:
                st.write(f"❓ Questions: {len(question_selected)} questions")
            
            st.write(f"🤖 Models: {', '.join(selected_model_names)}")
            st.write(f"📏 Size: {selected_size.title()}")
            
            # Extract button
            if st.button("🚀 Start Selective Extraction", type="primary"):
                with st.spinner("Starting selective extraction..."):
                    response = trigger_selective_extraction(
                        selected_pdf.get("id"),
                        selected_fields,
                        selected_model_names,
                        selected_size
                    )
                    
                    if response and response.status_code == 200:
                        result = response.json()
                        st.success("Selective extraction started successfully!")
                        
                        # Show extraction details
                        st.write("**Extraction Details:**")
                        st.write(f"- Selected Fields: {len(result.get('selected_fields', []))}")
                        st.write(f"- Selected Models: {len(result.get('selected_models', []))}")
                        st.write(f"- Message: {result.get('message')}")
                        
                        if result.get("success"):
                            st.info("Check the PDF List page to view results once extraction completes.")
                        
                    else:
                        error_detail = ""
                        if response:
                            try:
                                error_data = response.json()
                                error_detail = error_data.get("detail", response.text)
                            except:
                                error_detail = response.text
                        st.error(f"Failed to start selective extraction: {error_detail}")
        
        else:
            st.warning("Please select at least one field to extract.")
    
    st.markdown("---")
    st.info("💡 Use this page to extract only specific fields you need, saving time and resources. You can select different combinations of summary types, questions, models, and sizes based on your requirements.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**PDF Processor Dashboard**")
st.sidebar.markdown("Built with Streamlit & FastAPI")
st.sidebar.markdown("✨ Now with PDF Conversion & Extraction!")
