use wasm_bindgen::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct CorrelationResult {
    pub pearson: f64,
    pub spearman: f64,
    pub r_squared: f64,
    pub n: usize,
    pub strength: String,
    pub direction: String,
    pub slope: f64,
    pub intercept: f64,
    pub p_value_approx: f64,
}

#[derive(Serialize, Deserialize)]
pub struct DatasetStats {
    pub count: usize,
    pub mean: f64,
    pub median: f64,
    pub std_dev: f64,
    pub min: f64,
    pub max: f64,
    pub q1: f64,
    pub q3: f64,
    pub skewness: f64,
}

#[derive(Serialize, Deserialize)]
pub struct MatrixResult {
    pub ids: Vec<String>,
    pub pearson: Vec<Vec<f64>>,
    pub spearman: Vec<Vec<f64>>,
    pub n_points: Vec<Vec<usize>>,
}

// --- Public WASM functions --------------------------------------------------

#[wasm_bindgen]
pub fn compute_correlation(x_json: &str, y_json: &str) -> String {
    let x: Vec<f64> = serde_json::from_str(x_json).unwrap_or_default();
    let y: Vec<f64> = serde_json::from_str(y_json).unwrap_or_default();

    let n = x.len().min(y.len());
    if n < 3 {
        return serde_json::to_string(&CorrelationResult {
            pearson: 0.0, spearman: 0.0, r_squared: 0.0, n,
            strength: "insufficient data".into(), direction: "none".into(),
            slope: 0.0, intercept: 0.0, p_value_approx: 1.0,
        }).unwrap();
    }

    let x = &x[..n];
    let y = &y[..n];

    let pearson = pearson_correlation(x, y);
    let spearman = spearman_correlation(x, y);
    let r_squared = pearson * pearson;
    let (slope, intercept) = linear_regression(x, y);
    let p_value = approx_p_value(pearson, n);

    let abs_p = pearson.abs();
    let strength = if abs_p > 0.8 { "very strong" }
        else if abs_p > 0.6 { "strong" }
        else if abs_p > 0.4 { "moderate" }
        else if abs_p > 0.2 { "weak" }
        else { "negligible" };

    let direction = if pearson > 0.05 { "positive" }
        else if pearson < -0.05 { "negative" }
        else { "none" };

    serde_json::to_string(&CorrelationResult {
        pearson, spearman, r_squared, n,
        strength: strength.into(),
        direction: direction.into(),
        slope, intercept,
        p_value_approx: p_value,
    }).unwrap()
}

#[wasm_bindgen]
pub fn compute_stats(data_json: &str) -> String {
    let mut data: Vec<f64> = serde_json::from_str(data_json).unwrap_or_default();
    let data: Vec<f64> = data.into_iter().filter(|v| v.is_finite()).collect();

    if data.is_empty() {
        return serde_json::to_string(&DatasetStats {
            count: 0, mean: 0.0, median: 0.0, std_dev: 0.0,
            min: 0.0, max: 0.0, q1: 0.0, q3: 0.0, skewness: 0.0,
        }).unwrap();
    }

    let n = data.len();
    let mean = data.iter().sum::<f64>() / n as f64;
    let variance = data.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n as f64;
    let std_dev = variance.sqrt();

    let mut sorted = data.clone();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let median = percentile(&sorted, 0.5);
    let q1 = percentile(&sorted, 0.25);
    let q3 = percentile(&sorted, 0.75);

    let skewness = if std_dev > 0.0 {
        let m3 = data.iter().map(|x| ((x - mean) / std_dev).powi(3)).sum::<f64>();
        m3 / n as f64
    } else { 0.0 };

    serde_json::to_string(&DatasetStats {
        count: n, mean, median, std_dev,
        min: sorted[0], max: sorted[n - 1],
        q1, q3, skewness,
    }).unwrap()
}

#[wasm_bindgen]
pub fn normalize_series(data_json: &str) -> String {
    let data: Vec<f64> = serde_json::from_str(data_json).unwrap_or_default();
    if data.is_empty() { return "[]".into(); }

    let min = data.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = data.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let range = max - min;

    let normalized: Vec<f64> = if range == 0.0 {
        vec![0.5; data.len()]
    } else {
        data.iter().map(|x| (x - min) / range).collect()
    };

    serde_json::to_string(&normalized).unwrap()
}

/// Compute NxN correlation matrix from multiple aligned datasets.
/// Input: JSON object { "ids": ["a","b",...], "datasets": [[1,2,3],[4,5,6],...] }
#[wasm_bindgen]
pub fn compute_matrix(input_json: &str) -> String {
    #[derive(Deserialize)]
    struct MatrixInput {
        ids: Vec<String>,
        datasets: Vec<Vec<f64>>,
    }

    let input: MatrixInput = match serde_json::from_str(input_json) {
        Ok(v) => v,
        Err(_) => return "{}".into(),
    };

    let n = input.ids.len();
    let mut pearson = vec![vec![0.0f64; n]; n];
    let mut spearman = vec![vec![0.0f64; n]; n];
    let mut n_points = vec![vec![0usize; n]; n];

    for i in 0..n {
        for j in 0..n {
            if i == j {
                pearson[i][j] = 1.0;
                spearman[i][j] = 1.0;
                n_points[i][j] = input.datasets[i].len();
                continue;
            }
            // Align by index (assumes pre-aligned datasets)
            let len = input.datasets[i].len().min(input.datasets[j].len());
            if len < 3 {
                n_points[i][j] = len;
                continue;
            }
            let a = &input.datasets[i][..len];
            let b = &input.datasets[j][..len];
            pearson[i][j] = pearson_correlation(a, b);
            spearman[i][j] = spearman_correlation(a, b);
            n_points[i][j] = len;
        }
    }

    serde_json::to_string(&MatrixResult { ids: input.ids, pearson, spearman, n_points }).unwrap()
}

/// Compute regression line Y values for charting.
#[wasm_bindgen]
pub fn regression_line(x_json: &str, y_json: &str) -> String {
    let x: Vec<f64> = serde_json::from_str(x_json).unwrap_or_default();
    let y: Vec<f64> = serde_json::from_str(y_json).unwrap_or_default();
    let n = x.len().min(y.len());
    if n < 2 { return "[]".into(); }

    let (slope, intercept) = linear_regression(&x[..n], &y[..n]);
    let line: Vec<f64> = x[..n].iter().map(|xi| slope * xi + intercept).collect();
    serde_json::to_string(&line).unwrap()
}

/// Moving average smoothing.
#[wasm_bindgen]
pub fn moving_average(data_json: &str, window: usize) -> String {
    let data: Vec<f64> = serde_json::from_str(data_json).unwrap_or_default();
    if data.is_empty() || window == 0 { return "[]".into(); }

    let w = window.min(data.len());
    let mut result = Vec::with_capacity(data.len());
    let mut sum: f64 = data[..w].iter().sum();

    for i in 0..data.len() {
        if i >= w {
            sum += data[i] - data[i - w];
        }
        let count = (i + 1).min(w);
        if i < w {
            sum = data[..=i].iter().sum();
        }
        result.push(sum / count as f64);
    }

    serde_json::to_string(&result).unwrap()
}

// --- Internal math ----------------------------------------------------------

fn pearson_correlation(x: &[f64], y: &[f64]) -> f64 {
    let n = x.len() as f64;
    let mean_x = x.iter().sum::<f64>() / n;
    let mean_y = y.iter().sum::<f64>() / n;

    let mut cov = 0.0;
    let mut var_x = 0.0;
    let mut var_y = 0.0;

    for i in 0..x.len() {
        let dx = x[i] - mean_x;
        let dy = y[i] - mean_y;
        cov += dx * dy;
        var_x += dx * dx;
        var_y += dy * dy;
    }

    let denom = (var_x * var_y).sqrt();
    if denom == 0.0 { 0.0 } else { cov / denom }
}

fn spearman_correlation(x: &[f64], y: &[f64]) -> f64 {
    let ranks_x = compute_ranks(x);
    let ranks_y = compute_ranks(y);
    pearson_correlation(&ranks_x, &ranks_y)
}

fn compute_ranks(data: &[f64]) -> Vec<f64> {
    let n = data.len();
    let mut indexed: Vec<(usize, f64)> = data.iter().copied().enumerate().collect();
    indexed.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

    let mut ranks = vec![0.0; n];
    let mut i = 0;
    while i < n {
        let mut j = i;
        while j < n - 1 && indexed[j + 1].1 == indexed[j].1 {
            j += 1;
        }
        let avg_rank = (i + j) as f64 / 2.0 + 1.0;
        for k in i..=j {
            ranks[indexed[k].0] = avg_rank;
        }
        i = j + 1;
    }
    ranks
}

fn linear_regression(x: &[f64], y: &[f64]) -> (f64, f64) {
    let n = x.len() as f64;
    let mean_x = x.iter().sum::<f64>() / n;
    let mean_y = y.iter().sum::<f64>() / n;

    let mut ss_xy = 0.0;
    let mut ss_xx = 0.0;
    for i in 0..x.len() {
        let dx = x[i] - mean_x;
        ss_xy += dx * (y[i] - mean_y);
        ss_xx += dx * dx;
    }

    if ss_xx == 0.0 { return (0.0, mean_y); }
    let slope = ss_xy / ss_xx;
    let intercept = mean_y - slope * mean_x;
    (slope, intercept)
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    let n = sorted.len();
    if n == 0 { return 0.0; }
    if n == 1 { return sorted[0]; }
    let idx = p * (n - 1) as f64;
    let lo = idx.floor() as usize;
    let hi = idx.ceil() as usize;
    let frac = idx - lo as f64;
    sorted[lo] * (1.0 - frac) + sorted[hi] * frac
}

fn approx_p_value(r: f64, n: usize) -> f64 {
    // Approximate p-value using t-distribution approximation
    if n < 3 { return 1.0; }
    let n_f = n as f64;
    let t = r * ((n_f - 2.0) / (1.0 - r * r)).sqrt();
    let df = n_f - 2.0;
    // Simple approximation: use normal distribution for large df
    let p = (-0.5 * t * t / df * (df / (df - 2.0).max(1.0))).exp();
    p.min(1.0).max(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_perfect_positive() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let r = pearson_correlation(&x, &x);
        assert!((r - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_perfect_negative() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        let r = pearson_correlation(&x, &y);
        assert!((r + 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_regression() {
        let x = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let y = vec![2.0, 4.0, 6.0, 8.0, 10.0];
        let (slope, intercept) = linear_regression(&x, &y);
        assert!((slope - 2.0).abs() < 1e-10);
        assert!(intercept.abs() < 1e-10);
    }

    #[test]
    fn test_matrix() {
        let input = r#"{"ids":["a","b"],"datasets":[[1,2,3,4,5],[5,4,3,2,1]]}"#;
        let result: MatrixResult = serde_json::from_str(&compute_matrix(input)).unwrap();
        assert!((result.pearson[0][1] + 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_stats() {
        let input = "[1,2,3,4,5]";
        let stats: DatasetStats = serde_json::from_str(&compute_stats(input)).unwrap();
        assert!((stats.mean - 3.0).abs() < 1e-10);
        assert!((stats.median - 3.0).abs() < 1e-10);
    }
}
